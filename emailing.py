import argparse
import json
import os
import re
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import requests
from dotenv import load_dotenv

from linkedin_scraper import LinkedInScraper

# Load environment variables
load_dotenv()

# Configure logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("emailing.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Define common column mappings - specifically matching Contacts - Sheet1.csv format
COLUMN_MAPPINGS = {
    "linkedin_url": [
        "linkedin_url",
        "linkedin url",
        "linkedin ids",
        "profile url",
        "linkedin",
    ],
    "email": ["email", "email id", "valid emails", "email address"],
    "name": ["name", "full name", "contact name"],
    "company": ["company", "current employer", "employer", "account name"],
    "position": ["position", "title", "current position", "job title", "headline"],
    "location": ["location", "city", "state", "country"],
    "about": ["about", "bio", "summary", "description"],
    "aum": ["aum", "assets under management"],
    "account_type": ["account type", "account_type", "type"],
    "contact_type": ["contact type", "contact_type", "role"],
}


class EmailProcessor:
    def __init__(self, template, subject, test_mode=False):
        """
        Initialize the email processor

        Args:
            template (str): Email template with placeholders
            subject (str): Email subject line
            test_mode (bool): If True, don't actually send emails
        """
        self.template = template
        self.subject = subject
        self.test_mode = test_mode
        self.body_to_csv = False  # New option to save bodies to CSV instead of sending
        self.email_bodies = []  # Storage for email bodies when using body_to_csv

        # Initialize LinkedIn scraper
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL")
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD")
        self.rr_api_key = os.getenv("RR_API_KEY")

        # Initialize Claude API settings
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.claude_api_url = "https://api.anthropic.com/v1/messages"

        # Initialize SMTP settings
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))

        # Initialize LinkedIn scraper
        self.scraper = None

        # Initialize results tracking
        self.results = {"total": 0, "sent": 0, "failed": 0, "details": []}

    def setup_linkedin_scraper(self):
        """Set up and log in to LinkedIn"""
        try:
            logger.info("Setting up LinkedIn scraper...")
            self.scraper = LinkedInScraper(
                email=self.linkedin_email,
                password=self.linkedin_password,
                rr_api_key=self.rr_api_key,
            )
            self.scraper.setup_driver()

            if not self.scraper.login():
                logger.error("Failed to log in to LinkedIn")
                return False

            logger.info("Successfully logged in to LinkedIn")
            return True
        except Exception as e:
            logger.error(f"Error setting up LinkedIn scraper: {e}")
            return False

    def get_profile_data(self, linkedin_url):
        """
        Get profile data from LinkedIn

        Args:
            linkedin_url (str): LinkedIn profile URL

        Returns:
            dict: Profile data
        """
        try:
            logger.info(f"Scraping profile: {linkedin_url}")
            profile_data = self.scraper.scrape_profile(linkedin_url)
            return profile_data
        except Exception as e:
            logger.error(f"Error scraping profile {linkedin_url}: {e}")
            return None

    def map_columns(self, df):
        """
        Map CSV columns to standardized names based on common patterns

        Args:
            df (pandas.DataFrame): DataFrame from CSV

        Returns:
            dict: Mapping of standardized names to actual column names
        """
        column_map = {}
        df_columns_lower = [col.lower() for col in df.columns]

        # For each standard field, find the matching column in the DataFrame
        for standard_field, possible_names in COLUMN_MAPPINGS.items():
            for name in possible_names:
                if name in df_columns_lower:
                    # Find the original case-sensitive column name
                    original_col = df.columns[df_columns_lower.index(name)]
                    column_map[standard_field] = original_col
                    break

        logger.info(f"Column mapping: {json.dumps(column_map, indent=2)}")
        return column_map

    def extract_emails_from_list(self, email_list):
        """Extract valid emails from a list or string representation of a list"""
        if not email_list:
            return []

        # If the input is a string, try to parse it
        if isinstance(email_list, str):
            # Try to handle various string formats like "[]", "[email@example.com]", etc.
            email_list = email_list.strip("[]() ")
            if not email_list:
                return []

            # Handle comma-separated lists
            if "," in email_list:
                emails = [e.strip("' \"") for e in email_list.split(",")]
                return [e for e in emails if self.is_valid_email(e)]

            # Single email
            if self.is_valid_email(email_list):
                return [email_list]

            return []

        # If it's already a list
        elif isinstance(email_list, list):
            return [e for e in email_list if self.is_valid_email(e)]

        return []

    def is_valid_email(self, email):
        """Check if a string is a valid email address"""
        if not isinstance(email, str):
            return False

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    def personalize_email(self, contact_data, template):
        """
        Use OpenAI to personalize the email based on contact data

        Args:
            contact_data (dict): Contact data from CSV and/or LinkedIn
            template (str): Email template with placeholders

        Returns:
            str: Personalized email
        """
        try:
            # Extract key information with fallbacks
            name = contact_data.get("Name", "N/A")
            first_name = name.split()[0] if name and name != "N/A" else "there"

            # First, replace the first_name placeholder
            basic_template = re.sub(r'\{\{first_name:"[^"]*"\}\}', first_name, template)

            # Format additional context for better personalization
            context_info = []

            # Add key profile data - using exact column names from the CSV
            if "Title" in contact_data and contact_data["Title"]:
                context_info.append(f"- Role/Title: {contact_data['Title']}")

            if "Account Name" in contact_data and contact_data["Account Name"]:
                context_info.append(
                    f"- Company/Employer: {contact_data['Account Name']}"
                )

            # Add financial industry specific information
            if "AUM" in contact_data and contact_data["AUM"]:
                context_info.append(f"- Assets Under Management: {contact_data['AUM']}")

            if "Account Type" in contact_data and contact_data["Account Type"]:
                context_info.append(f"- Account Type: {contact_data['Account Type']}")

            if "Contact Type" in contact_data and contact_data["Contact Type"]:
                context_info.append(f"- Contact Type: {contact_data['Contact Type']}")

            # Add any other available data
            for key, value in contact_data.items():
                if (
                    key
                    not in [
                        "Name",
                        "Title",
                        "Account Name",
                        "AUM",
                        "Account Type",
                        "Contact Type",
                        "LinkedIn IDs",
                        "Email ID",
                    ]
                    and value
                    and str(value).lower() not in ["n/a", "nan", "none", ""]
                ):
                    context_info.append(f"- {key}: {value}")

            context_text = "\n".join(context_info)

            # Prompt for OpenAI to fill in the rest - tailored for financial advisors
            prompt = f"""
You are an AI assistant helping to personalize an email for a venture capital outreach.

Here is the recipient's information:
- Name: {name}
{context_text}

Here is the email template with xxx placeholders that need to be replaced:
{basic_template}

Please personalize the email by:
- Address the recipient by name
1. Replacing 'xxx at xxxxxxx' with specific details about their experience/role as a financial advisor
2. Mention their experience managing assets (AUM: {contact_data.get("AUM", "N/A")}) and their role at {contact_data.get("Account Name", "their firm")}
3. Keep the tone professional but conversational
4. Don't make up information that isn't in their profile
5. Don't change any other part of the template
6. Focus specifically on their financial advisory experience and how it relates to private market investments
7. If they are a Portfolio Manager, emphasize that aspect of their experience

Return only the completed email text without explanations.
"""

            # Using Claude API for personalization
            headers = {
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "system": "You are a helpful assistant that personalizes emails for financial industry professionals.",
                "messages": [{"role": "user", "content": prompt}],
            }

            response = requests.post(self.claude_api_url, headers=headers, json=data)

            if response.status_code == 200:
                response_data = response.json()
                personalized_email = response_data["content"][0]["text"].strip()
            else:
                logger.error(
                    f"Claude API Error: {response.status_code} - {response.text}"
                )
                raise Exception(f"Claude API Error: {response.status_code}")
            return personalized_email

        except Exception as e:
            logger.error(f"Error personalizing email: {e}")
            # Fall back to basic personalization
            return template.replace('{{first_name:"there"}}', first_name)

    def send_email(self, to_email, personalized_email, contact_data=None):
        """
        Send an email or store it for CSV export

        Args:
            to_email (str): Recipient email
            personalized_email (str): Personalized email content
            contact_data (dict, optional): Contact data for CSV export

        Returns:
            bool: True if sent/stored successfully, False otherwise
        """
        # If we're saving to CSV instead of sending
        if self.body_to_csv:
            try:
                # Store the email body along with recipient info
                email_entry = {
                    "email": to_email,
                    "subject": self.subject,
                    "body": personalized_email,
                }

                # Add any available contact data
                if contact_data:
                    for key, value in contact_data.items():
                        if key not in email_entry:
                            email_entry[key] = value

                self.email_bodies.append(email_entry)
                logger.info(f"Stored email body for {to_email} (for CSV export)")
                return True
            except Exception as e:
                logger.error(f"Error storing email body for {to_email}: {e}")
                return False

        # Standard email sending logic
        if self.test_mode:
            logger.info(f"TEST MODE: Would send to {to_email}")
            logger.info(f"Email content:\n{personalized_email}")
            return True

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.smtp_username
            msg["To"] = to_email
            msg["Subject"] = self.subject

            # Attach email body
            msg.attach(MIMEText(personalized_email, "plain"))

            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    def process_csv(self, csv_path, limit=None):
        """
        Process a CSV file of contacts

        Args:
            csv_path (str): Path to CSV file
            limit (int, optional): Maximum number of contacts to process
        """
        # Set up LinkedIn scraper if not already done
        if not self.scraper:
            if not self.setup_linkedin_scraper():
                logger.error("Failed to set up LinkedIn scraper. Exiting.")
                return

        # Load CSV data
        try:
            # First try with regular encoding
            try:
                # Check if this is the specific "Contacts - Sheet1.csv" format with unnamed columns
                df = pd.read_csv(csv_path)

                # If first row has column names as values (common in Google Sheets exports)
                if (
                    all(col.startswith("Unnamed:") for col in df.columns)
                    and len(df) > 0
                ):
                    logger.info("Detected unnamed columns with headers in first row")

                    # Use the first row as column names
                    new_columns = df.iloc[0].values
                    df = df[1:]  # Drop the first row
                    df.columns = new_columns
                    df = df.reset_index(drop=True)

                    logger.info(f"New columns: {df.columns.tolist()}")
            except UnicodeDecodeError:
                # If that fails, try with different encodings
                df = pd.read_csv(csv_path, encoding="latin1")

                # Same check for unnamed columns
                if (
                    all(col.startswith("Unnamed:") for col in df.columns)
                    and len(df) > 0
                ):
                    logger.info("Detected unnamed columns with headers in first row")
                    new_columns = df.iloc[0].values
                    df = df[1:]
                    df.columns = new_columns
                    df = df.reset_index(drop=True)

            # Map columns to standardized names
            column_map = self.map_columns(df)

            # For "Contacts - Sheet1.csv" format, manually map the columns if automatic mapping fails
            if (
                "Name" in df.columns
                and "LinkedIn IDs" in df.columns
                and "Email ID" in df.columns
            ):
                logger.info(
                    "Detected 'Contacts - Sheet1.csv' format, using direct column mapping"
                )
                column_map = {
                    "linkedin_url": "LinkedIn IDs",
                    "email": "Email ID",
                    "name": "Name",
                    "company": "Account Name",
                    "position": "Title",
                }

            # Check if the required LinkedIn URL or email column exists
            if "linkedin_url" not in column_map and "email" not in column_map:
                logger.error(
                    f"CSV must have a column for LinkedIn URLs or emails. Available columns: {df.columns.tolist()}"
                )
                logger.error(
                    "Please rename one of these columns or provide a CSV with LinkedIn URL data."
                )
                return

            linkedin_col = column_map.get("linkedin_url")
            email_col = column_map.get("email")
            logger.info(f"Loaded {len(df)} contacts from {csv_path}")

            # Process each row (with optional limit)
            max_contacts = min(len(df), limit) if limit else len(df)
            logger.info(f"Processing {max_contacts} contacts (out of {len(df)} total)")

            for i, row in df.iloc[:max_contacts].iterrows():
                self.results["total"] += 1

                # Get LinkedIn URL if available
                linkedin_url = None
                if linkedin_col and linkedin_col in row and pd.notna(row[linkedin_col]):
                    linkedin_url = row[linkedin_col]

                result_details = {
                    "linkedin_url": linkedin_url if linkedin_url else "N/A",
                    "status": "pending",
                    "email_used": None,
                    "notes": "",
                }

                try:
                    # Create a normalized contact data dictionary
                    contact_data = {}

                    # Extract data from CSV row using our column mapping
                    for standard_field, csv_field in column_map.items():
                        if csv_field in row and pd.notna(row[csv_field]):
                            contact_data[standard_field] = row[csv_field]

                    # Add any unmapped columns that might be useful
                    for col in df.columns:
                        if pd.notna(row[col]) and col not in column_map.values():
                            # Convert to lowercase with underscores for consistency
                            field_name = col.lower().replace(" ", "_")
                            contact_data[field_name] = row[col]

                    # Get LinkedIn profile data if we have a URL and we're not skipping LinkedIn
                    linkedin_data = None
                    if (
                        self.scraper
                        and self.scraper is not True
                        and "linkedin_url" in contact_data
                        and contact_data["linkedin_url"]
                    ):
                        linkedin_data = self.get_profile_data(
                            contact_data["linkedin_url"]
                        )

                        # Merge LinkedIn data into contact_data, giving preference to CSV data
                        if linkedin_data:
                            # Standardize LinkedIn data keys
                            standardized_linkedin = {}
                            for key, value in linkedin_data.items():
                                # Convert to lowercase with underscores for consistency
                                std_key = key.lower().replace(" ", "_")
                                standardized_linkedin[std_key] = value

                            # Add LinkedIn data that's not already in contact_data
                            for key, value in standardized_linkedin.items():
                                if key not in contact_data or not contact_data[key]:
                                    contact_data[key] = value

                            # Handle special case for Valid Emails from LinkedIn
                            if (
                                "valid_emails" in standardized_linkedin
                                and standardized_linkedin["valid_emails"]
                            ):
                                emails = self.extract_emails_from_list(
                                    standardized_linkedin["valid_emails"]
                                )
                                if emails and (
                                    "email" not in contact_data
                                    or not contact_data["email"]
                                ):
                                    contact_data["email"] = emails[0]
                                    result_details["notes"] += (
                                        "Using email from RocketReach. "
                                    )
                    elif self.scraper is True:
                        result_details["notes"] += (
                            "Skipping LinkedIn scraping as requested. "
                        )

                    # Get email - prioritize the email from CSV mapping
                    email = None
                    if "email" in contact_data and contact_data["email"]:
                        if isinstance(contact_data["email"], list):
                            if contact_data["email"]:
                                email = contact_data["email"][0]
                        else:
                            email = str(contact_data["email"])
                        result_details["notes"] += "Using email from CSV. "

                    if not email:
                        result_details["status"] = "failed"
                        result_details["notes"] += "No email available."
                        self.results["failed"] += 1
                        self.results["details"].append(result_details)
                        continue

                    # Validate the email format
                    if not self.is_valid_email(email):
                        result_details["status"] = "failed"
                        result_details["notes"] += f"Invalid email format: {email}"
                        self.results["failed"] += 1
                        self.results["details"].append(result_details)
                        continue

                    result_details["email_used"] = email

                    # Personalize the email
                    personalized_email = self.personalize_email(
                        contact_data, self.template
                    )

                    # Send the email or store for CSV export
                    if self.send_email(email, personalized_email, contact_data):
                        if self.body_to_csv:
                            result_details["status"] = "stored"
                        else:
                            result_details["status"] = "sent"
                        self.results["sent"] += 1
                    else:
                        result_details["status"] = "failed"
                        if self.body_to_csv:
                            result_details["notes"] += "Failed to store email body."
                        else:
                            result_details["notes"] += "Failed to send email."
                        self.results["failed"] += 1

                except Exception as e:
                    result_details["status"] = "failed"
                    result_details["notes"] += f"Error: {str(e)}"
                    self.results["failed"] += 1
                    logger.error(f"Error processing row {i}: {e}")

                self.results["details"].append(result_details)

                # Pause between profiles to avoid rate limiting
                time.sleep(3)

        except pd.errors.EmptyDataError:
            logger.error(f"Error: The file {csv_path} is empty")
        except pd.errors.ParserError:
            logger.error(f"Error: The file {csv_path} is not a valid CSV file")
        except FileNotFoundError:
            logger.error(f"Error: The file {csv_path} does not exist")
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")

    def generate_report(self):
        """Generate a report of the email sending results"""
        mode = "TEST MODE" if self.test_mode else "LIVE MODE"
        if self.body_to_csv:
            mode += " (STORING TO CSV)"

        report = f"""
EMAIL SENDING REPORT
===================
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Mode: {mode}

SUMMARY
-------
Total contacts: {self.results["total"]}
Emails {"stored" if self.body_to_csv else "sent"}: {self.results["sent"]}
Failed: {self.results["failed"]}
Success rate: {self.results["sent"] / self.results["total"] * 100 if self.results["total"] > 0 else 0:.2f}%

DETAILS
-------
"""
        for detail in self.results["details"]:
            report += f"LinkedIn: {detail['linkedin_url']}\n"
            report += f"Status: {detail['status']}\n"
            report += f"Email: {detail['email_used']}\n"
            report += f"Notes: {detail['notes']}\n"
            report += "----------------\n"

        # Save report to file
        report_path = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, "w") as f:
            f.write(report)

        # If we're storing email bodies, save them to CSV
        if self.body_to_csv and self.email_bodies:
            try:
                csv_path = (
                    f"email_bodies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )

                # Create a modified DataFrame to handle newlines properly
                modified_bodies = []
                for entry in self.email_bodies:
                    # Create a new entry for each email to avoid modifying the original
                    new_entry = entry.copy()

                    # HTML encode the newlines so they render properly when viewed
                    if "body" in new_entry and new_entry["body"]:
                        new_entry["body"] = new_entry["body"].replace("\n", "<br>")

                    modified_bodies.append(new_entry)

                df = pd.DataFrame(modified_bodies)
                df.to_csv(csv_path, index=False)
                logger.info(f"Email bodies saved to {csv_path} with HTML line breaks")
            except Exception as e:
                logger.error(f"Error saving email bodies to CSV: {e}")

        logger.info(f"Report saved to {report_path}")
        return report

    def cleanup(self):
        """Clean up resources"""
        if self.scraper:
            self.scraper.close()
            logger.info("LinkedIn scraper closed")


def main():
    parser = argparse.ArgumentParser(
        description="Send personalized emails based on LinkedIn profiles"
    )
    parser.add_argument(
        "csv_file", help="Path to CSV file with LinkedIn URLs and optional emails"
    )
    parser.add_argument(
        "--subject", default="Connecting from 535West", help="Email subject line"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test mode - don't actually send emails"
    )
    parser.add_argument(
        "--show-columns", action="store_true", help="Show CSV columns and exit"
    )
    parser.add_argument(
        "--skip-linkedin",
        action="store_true",
        help="Skip LinkedIn scraping and just use CSV data",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of emails to send (for testing)",
    )
    parser.add_argument(
        "--body-to-csv",
        action="store_true",
        help="Save personalized email bodies to a CSV instead of sending emails",
    )
    args = parser.parse_args()

    # If show-columns flag is set, just display the CSV columns and exit
    if args.show_columns:
        try:
            # First load the raw CSV
            df = pd.read_csv(args.csv_file)
            print(f"\nRaw columns found in {args.csv_file}:")
            for i, col in enumerate(df.columns):
                print(f"{i + 1}. {col}")

            # Check if this is a CSV with unnamed columns and headers in first row
            if all(col.startswith("Unnamed:") for col in df.columns) and len(df) > 0:
                print("\nDetected unnamed columns with headers in first row")
                new_columns = df.iloc[0].values
                df = df[1:]  # Drop the first row
                df.columns = new_columns
                df = df.reset_index(drop=True)

                print("\nActual columns (from first row):")
                for i, col in enumerate(df.columns):
                    print(f"{i + 1}. {col}")

            print("\nSample data (first row):")
            for col in df.columns:
                if len(df) > 0:  # Make sure we have at least one row
                    value = df.iloc[0][col]
                    print(f"{col}: {value}")

            return
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return

    # Default template
    template = """Hey {{first_name:"there"}},

I'm Rahil from 535West, a tech-focused venture fund with investments in companies like Databricks, SpaceX, OpenAI, Apptronik, and more. 

Given your investment background and your experience doing xxx at xxxxxxx, I'd love to connect and learn more about your approach to private market investments. Would you be open to a quick introductory call sometime in the coming weeks?

Looking forward to connecting!

Best,
Rahil"""

    try:
        processor = EmailProcessor(template, args.subject, args.test)

        # Only set up LinkedIn scraper if not skipping LinkedIn
        if args.skip_linkedin:
            logger.info("Skipping LinkedIn scraping as requested")
            processor.scraper = True  # Set a dummy value so setup isn't attempted

        # Add parameter to store body-to-csv option
        processor.body_to_csv = args.body_to_csv

        processor.process_csv(args.csv_file, limit=args.limit)
        report = processor.generate_report()

        # Only need to cleanup if we actually initialized the scraper
        if not args.skip_linkedin:
            processor.cleanup()

        if processor.body_to_csv:
            print("\nEmail Processing Complete!")
            print(f"Emails stored in CSV: {processor.results['sent']}")
            print(f"Failed: {processor.results['failed']}")
        else:
            print("\nEmail Sending Complete!")
            print(f"Sent: {processor.results['sent']}")
            print(f"Failed: {processor.results['failed']}")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Cleaning up...")
        if "processor" in locals():
            processor.cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if "processor" in locals():
            processor.cleanup()


if __name__ == "__main__":
    main()
