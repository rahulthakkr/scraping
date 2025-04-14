import os
import time

import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class RocketReachBrowser:
    def __init__(self, email=None, password=None):
        """Initialize the RocketReach browser automation with login credentials."""
        load_dotenv()  # Load environment variables
        self.email = email or os.getenv("ROCKETREACH_EMAIL")
        self.password = password or os.getenv("ROCKETREACH_PASSWORD")
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """Set up the Chrome WebDriver."""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")  # Start maximized
        chrome_options.add_argument("--disable-notifications")  # Disable notifications

        # Initialize Chrome WebDriver with options
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Log in to RocketReach."""
        try:
            self.driver.get("https://rocketreach.co/login")
            time.sleep(2)

            # Enter email - updated ID
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "id_email"))
            )
            email_field.send_keys(self.email)

            # Enter password - updated ID
            password_field = self.driver.find_element(By.ID, "id_password")
            password_field.send_keys(self.password)

            # Check for reCAPTCHA - this is a simple detection, not solving it automatically
            try:
                recaptcha = self.driver.find_element(By.ID, "RecaptchaInput")
                if recaptcha:
                    print("CAPTCHA detected! You may need to manually solve it.")
                    # Give user time to solve CAPTCHA if needed
                    input("Press Enter after you've solved the CAPTCHA (if needed)...")
            except NoSuchElementException:
                # No CAPTCHA or it's already handled
                pass

            # Click login button
            login_button = self.driver.find_element(
                By.XPATH, "//button[@type='submit']"
            )
            login_button.click()

            # Wait for login to complete
            time.sleep(5)

            # Check for error messages
            try:
                error_message = self.driver.find_element(
                    By.XPATH,
                    "//ul[contains(@class, 'error-messages')]//li[not(contains(@class, 'ng-hide'))]",
                )
                if error_message:
                    print(f"Login error: {error_message.text}")
                    return False
            except NoSuchElementException:
                # No visible error message
                pass

            # Check if login was successful by looking for dashboard elements
            try:
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(@href, '/search')]")
                    )
                )
                print("RocketReach login successful!")
                return True
            except TimeoutException:
                # Alternative check - sometimes the dashboard has a different structure
                try:
                    self.wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[contains(@class, 'dashboard')]")
                        )
                    )
                    print("RocketReach login successful!")
                    return True
                except TimeoutException:
                    # One more check - see if we can find any element that suggests we're logged in
                    if (
                        "/person" in self.driver.current_url
                        or "/dashboard" in self.driver.current_url
                    ):
                        print("RocketReach login appears successful (based on URL).")
                        return True

                    print("RocketReach login failed. Please check your credentials.")
                    return False

        except Exception as e:
            print(f"Error during RocketReach login: {e}")
            return False

    def search_by_linkedin_url(self, linkedin_url):
        """
        Search for a profile on RocketReach using a LinkedIn URL.

        Args:
            linkedin_url: The LinkedIn profile URL

        Returns:
            Dictionary with extracted profile data or None if search failed
        """
        try:
            # Navigate to the search page (Person Search)
            self.driver.get("https://rocketreach.co/person")
            # Wait for the search page to load (look for a stable element like the filter header)
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'search-input-header')]")
                )
            )

            # Find the general keyword search input field using its placeholder
            search_input = self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        # Using the placeholder for the general search input
                        "//input[@placeholder='e.g. LinkedIn URL, Job Title, Industry, Revenue, Number of Employees, Years of Experience, etc.']",
                    )
                )
            )
            search_input.clear()
            search_input.send_keys(linkedin_url)
            time.sleep(0.5)  # Brief pause for JS/UI updates after input
            search_input.send_keys(Keys.RETURN)  # Simulate pressing Enter

            # Wait for search results to appear after submitting the search
            try:
                # Look for the container holding search result cards
                results_container = self.wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//div[contains(@class, 'search-results')]",  # Wait for the main results area
                        )
                    )
                )
                # Now specifically wait for at least one person card within that container
                first_result = self.wait.until(
                    EC.element_to_be_clickable(  # Ensure it's clickable
                        (
                            By.XPATH,
                            ".//div[contains(@class, 'person-card')]",  # Search within results_container
                        )
                    ),
                    message=f"No clickable person card found for LinkedIn URL: {linkedin_url}",
                )

                # Ensure the element is visible before clicking
                self.wait.until(
                    EC.visibility_of(first_result),
                    message=f"First result card not visible for LinkedIn URL: {linkedin_url}",
                )

                # Scroll the element into view before clicking
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", first_result
                )
                time.sleep(1.0)  # Increased pause after scroll

                # Click on the first search result using JavaScript
                self.driver.execute_script("arguments[0].click();", first_result)
                # first_result.click() # Original click commented out

                # Wait for the profile page to load (e.g., wait for the name element)
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//h1[contains(@class, 'name')]")
                    )
                )
                time.sleep(1)  # Add a small pause after profile loads

                # --- Click 'Get Contact Info' button --- START
                try:
                    get_contact_button = self.wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//button[contains(., 'Get Contact Info') and not(@disabled)]",
                            )
                        )
                    )
                    # Scroll button into view if necessary
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", get_contact_button
                    )
                    time.sleep(0.5)
                    get_contact_button.click()
                    print("Clicked 'Get Contact Info' button.")
                    time.sleep(3)  # Wait for contact info to potentially reveal
                except (NoSuchElementException, TimeoutException):
                    print(
                        "'Get Contact Info' button not found or not clickable (might be disabled or info already shown)."
                    )
                # --- Click 'Get Contact Info' button --- END

                # Now we're on the profile page, extract data
                return self.extract_profile_data()

            except TimeoutException:
                print(f"No results found or loaded for LinkedIn URL: {linkedin_url}")
                return None

        except Exception as e:
            print(f"Error searching by LinkedIn URL '{linkedin_url}': {e}")
            return None

    def extract_profile_data(self):
        """
        Extract data from the current RocketReach profile page.

        Returns:
            Dictionary with profile data
        """
        profile_data = {}

        try:
            # Extract name
            name_elem = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h1[contains(@class, 'name')]")
                )
            )
            profile_data["name"] = name_elem.text.strip()
        except (NoSuchElementException, TimeoutException):
            profile_data["name"] = "N/A"

        try:
            # Extract title
            title_elem = self.driver.find_element(
                By.XPATH, "//div[contains(@class, 'title')]"
            )
            profile_data["title"] = title_elem.text.strip()
        except NoSuchElementException:
            profile_data["title"] = "N/A"

        try:
            # Extract company
            company_elem = self.driver.find_element(
                By.XPATH, "//div[contains(@class, 'company')]"
            )
            profile_data["company"] = company_elem.text.strip()
        except NoSuchElementException:
            profile_data["company"] = "N/A"

        # Extract contact information - check for revealed emails
        try:
            # Look for revealed emails section
            revealed_emails = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'email-section')]//span[contains(@class, 'verified')]",
            )
            if revealed_emails:
                profile_data["email"] = revealed_emails[0].text.strip()
            else:
                # Check if "Reveal Email" button exists
                reveal_button = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Reveal Email')]"
                )
                if reveal_button:
                    print("Email exists but needs to be revealed (requires credits)")
                    profile_data["email"] = "Needs Credits to Reveal"
                else:
                    profile_data["email"] = "Not Available"
        except NoSuchElementException:
            profile_data["email"] = "Not Available"

        try:
            # Extract phone if revealed
            revealed_phones = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'phone-section')]//span[contains(@class, 'verified')]",
            )
            if revealed_phones:
                profile_data["phone"] = revealed_phones[0].text.strip()
            else:
                # Check if "Reveal Phone" button exists
                reveal_phone_button = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Reveal Phone')]"
                )
                if reveal_phone_button:
                    print("Phone exists but needs to be revealed (requires credits)")
                    profile_data["phone"] = "Needs Credits to Reveal"
                else:
                    profile_data["phone"] = "Not Available"
        except NoSuchElementException:
            profile_data["phone"] = "Not Available"

        # Extract social links
        try:
            linkedin_elem = self.driver.find_element(
                By.XPATH, "//a[contains(@href, 'linkedin.com')]"
            )
            profile_data["linkedin_url"] = linkedin_elem.get_attribute("href")
        except NoSuchElementException:
            # If we're here, we already have the LinkedIn URL that was used for the search
            pass

        try:
            twitter_elem = self.driver.find_element(
                By.XPATH, "//a[contains(@href, 'twitter.com')]"
            )
            profile_data["twitter"] = twitter_elem.get_attribute("href")
        except NoSuchElementException:
            profile_data["twitter"] = "N/A"

        try:
            # Extract company website
            website_elem = self.driver.find_element(
                By.XPATH, "//a[contains(@class, 'website-link')]"
            )
            profile_data["website"] = website_elem.get_attribute("href")
        except NoSuchElementException:
            profile_data["website"] = "N/A"

        return profile_data

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()


def main():
    # Initialize the RocketReach browser
    rr_browser = RocketReachBrowser()

    try:
        # Setup and login
        rr_browser.setup_driver()
        if not rr_browser.login():
            print("Unable to login to RocketReach. Exiting.")
            rr_browser.close()
            return

        # Ask for LinkedIn profiles file
        linkedin_file = input("Enter the path to the CSV file with LinkedIn profiles: ")
        if not os.path.exists(linkedin_file):
            print(f"File not found: {linkedin_file}")
            rr_browser.close()
            return

        # Read the LinkedIn profiles
        try:
            df = pd.read_csv(linkedin_file)
            # Check if the required column exists before trying to rename
            if "Profile URL" not in df.columns:
                print("The CSV file must have a 'Profile URL' column.")
                rr_browser.close()
                return
            df["linkedin_url"] = df["Profile URL"]  # Rename for consistency internally
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            rr_browser.close()
            return

        # Create a list to store the enriched data
        enriched_data = []

        # Process each LinkedIn URL
        for index, row in df.iterrows():
            linkedin_url = row["linkedin_url"]
            print(f"Processing {index + 1}/{len(df)}: {linkedin_url}")

            # Search for the profile on RocketReach
            profile_data = rr_browser.search_by_linkedin_url(linkedin_url)

            if profile_data:
                # Combine the LinkedIn data with RocketReach data
                combined_data = {**row.to_dict(), **profile_data}
                enriched_data.append(combined_data)
                print(
                    f"Successfully enriched profile: {profile_data.get('name', 'Unknown')}"
                )
            else:
                # Keep the original data
                enriched_data.append(row.to_dict())
                print(f"Could not enrich profile for URL: {linkedin_url}")

            # Avoid rate limiting
            time.sleep(2)

        # Save the enriched data to a new CSV file
        output_file = linkedin_file.replace(".csv", "_enriched.csv")
        pd.DataFrame(enriched_data).to_csv(output_file, index=False)
        print(f"Enriched data saved to: {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        rr_browser.close()


if __name__ == "__main__":
    main()
