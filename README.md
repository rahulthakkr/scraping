# LinkedIn Profile Scraper and Email Automation

A Python toolset for searching LinkedIn profiles, extracting information, and sending personalized emails for outreach.

## Features

### LinkedIn Scraper
- Automated login to LinkedIn
- Search for people using specific keywords (e.g., "founder")
- Visit profiles and extract information:
  - Name
  - Headline
  - Location
  - About section
  - Current position
  - Profile URL
- Save all data to a CSV file

### Email Automation
- Read contact data and emails from CSV files (primary source)
- Personalize emails using Claude AI based on available CSV data
- Optionally enhance personalization with LinkedIn profile info
- Send batch emails with proper tracking and reporting

## Requirements

- Python 3.6+
- Chrome browser installed (see chrome_setup_guide.md for setup instructions)
- LinkedIn account
- Claude API key
- SMTP email account for sending emails

## Installation

1. Clone this repository or download the scripts
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## LinkedIn Scraper Usage

1. Open the `linkedin_scraper.py` file and replace the placeholder credentials with your LinkedIn login information:

```python
# Replace with your LinkedIn credentials
EMAIL = "your_email@example.com"
PASSWORD = "your_password"
```

2. Customize the search term and number of pages to scrape:

```python
# Search term and number of pages to scrape
SEARCH_TERM = "founder"
NUM_PAGES = 3
```

3. Run the script:

```bash
python linkedin_scraper.py
```

The script will:
- Log in to LinkedIn using your credentials
- Search for people with the specified search term
- Visit each profile and extract information
- Save the data to a CSV file

## Email Automation Usage

The `emailing.py` script reads a CSV file with contact information (including email addresses), personalizes emails using Claude AI based on the CSV data, and sends them. It can optionally scrape LinkedIn profiles for additional context to enhance personalization.

### CSV Format

The CSV file should contain at least the following columns:
- LinkedIn IDs (LinkedIn profile URLs)
- Email ID (contact email addresses)

Additional columns that enhance personalization:
- Name
- Account Name (company/employer)
- Title (job title/position)
- AUM (Assets Under Management) 
- Account Type
- Contact Type

### Environment Variables

Create a `.env` file with these variables:

```
# LinkedIn credentials
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password

# RocketReach API key (optional)
RR_API_KEY=your_rocketreach_api_key

# Claude API key
CLAUDE_API_KEY=your_claude_api_key

# Email sending settings
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Running Email Automation

```bash
# Show help
python emailing.py --help

# Send test emails (doesn't actually send, just shows what would be sent)
python emailing.py your_csv_file.csv --test

# Skip LinkedIn scraping and just use CSV data
python emailing.py your_csv_file.csv --skip-linkedin

# Limit the number of emails for testing
python emailing.py your_csv_file.csv --test --limit 5

# Show the columns in your CSV file
python emailing.py your_csv_file.csv --show-columns

# Send real emails with custom subject
python emailing.py your_csv_file.csv --subject "Your custom subject line"
```

## Important Notes

- LinkedIn may detect and block automated scraping. Use this script responsibly and at your own risk.
- Add random delays between actions to avoid detection.
- LinkedIn's HTML structure may change over time, requiring updates to the XPath selectors.
- This script is for educational purposes only. Always respect LinkedIn's Terms of Service.
- Ensure compliance with email regulations (CAN-SPAM, GDPR, etc.) when sending emails.

## Troubleshooting

- If you encounter login issues, try increasing the sleep time after login.
- If profile data is not being extracted correctly, check and update the XPath selectors.
- If you get blocked by LinkedIn, try using a different IP address or wait before trying again.
- Use `--test` mode to verify emails before actually sending them.