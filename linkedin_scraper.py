import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class LinkedInScraper:
    def __init__(self, email, password):
        """Initialize the LinkedIn scraper with login credentials."""
        self.email = email
        self.password = password
        self.driver = None
        self.data = []

    def setup_driver(self):
        """Set up the Safari WebDriver."""
        # Safari doesn't use options like Chrome does
        self.driver = webdriver.Safari()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Log in to LinkedIn."""
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)

            # Enter email
            email_field = self.driver.find_element(By.ID, "username")
            email_field.send_keys(self.email)

            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)

            # Click login button
            login_button = self.driver.find_element(
                By.XPATH, "//button[@type='submit']"
            )
            login_button.click()

            # Wait for login to complete
            time.sleep(5)

            # Check if login was successful
            if (
                "feed" in self.driver.current_url
                or "checkpoint" in self.driver.current_url
            ):
                print("Login successful!")
                return True
            else:
                print("Login failed. Please check your credentials.")
                return False

        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def search_people(self, search_term, num_pages=3):
        """Search for people with the given search term and scrape their profiles."""
        try:
            # Navigate to LinkedIn search page for people
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_term.replace(' ', '%20')}"
            self.driver.get(search_url)
            time.sleep(5)  # Increased wait time for page to load

            print(f"Searching for '{search_term}' on LinkedIn...")

            profiles_scraped = 0

            for page in range(1, num_pages + 1):
                print(f"Scraping page {page} of search results...")

                # Take a screenshot to debug
                screenshot_path = f"search_page_{page}.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"Saved screenshot to {screenshot_path}")

                # Try different XPath patterns for profile links
                profile_links = []

                # Pattern 1: Standard entity-result pattern
                try:
                    links1 = self.driver.find_elements(
                        By.XPATH, "//span[@class='entity-result__title-text']/a"
                    )
                    profile_links.extend(links1)
                    print(f"Found {len(links1)} links with pattern 1")
                except:
                    pass

                # Pattern 2: Alternative pattern
                try:
                    links2 = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(@class, 'app-aware-link') and contains(@href, '/in/')]",
                    )
                    profile_links.extend(links2)
                    print(f"Found {len(links2)} links with pattern 2")
                except:
                    pass

                # Pattern 3: Another alternative
                try:
                    links3 = self.driver.find_elements(
                        By.CSS_SELECTOR, "a.search-result__result-link"
                    )
                    profile_links.extend(links3)
                    print(f"Found {len(links3)} links with pattern 3")
                except:
                    pass

                # Extract the href attributes
                profile_urls = []
                for link in profile_links:
                    try:
                        url = link.get_attribute("href")
                        if url and "/in/" in url:
                            profile_urls.append(url)
                    except:
                        continue

                # Remove duplicates
                profile_urls = list(set(profile_urls))

                print(f"Found {len(profile_urls)} unique profile URLs")

                # Visit each profile and extract data
                for url in profile_urls:
                    # Clean the URL to remove query parameters
                    clean_url = url.split("?")[0]

                    try:
                        self.scrape_profile(clean_url)
                        profiles_scraped += 1
                        time.sleep(3)  # Increased pause between profile visits
                    except Exception as e:
                        print(f"Error scraping profile {clean_url}: {e}")

                # Check if there's a next page and navigate to it
                if page < num_pages:
                    try:
                        # Try different patterns for the next button
                        next_button = None

                        # Pattern 1
                        try:
                            next_button = self.driver.find_element(
                                By.XPATH, "//button[@aria-label='Next']"
                            )
                        except:
                            pass

                        # Pattern 2
                        if not next_button:
                            try:
                                next_button = self.driver.find_element(
                                    By.XPATH,
                                    "//button[contains(@class, 'artdeco-pagination__button--next')]",
                                )
                            except:
                                pass

                        if next_button and next_button.is_enabled():
                            next_button.click()
                            time.sleep(5)  # Increased wait time for page to load
                        else:
                            print("No more pages available or Next button not found.")
                            break
                    except Exception as e:
                        print(f"Error navigating to next page: {e}")
                        break

            print(f"Successfully scraped {profiles_scraped} profiles.")

        except Exception as e:
            print(f"Error during search: {e}")

    def scrape_profile(self, profile_url):
        """Visit a profile and extract basic information."""
        try:
            print(f"Visiting profile: {profile_url}")
            self.driver.get(profile_url)
            time.sleep(5)  # Increased wait time for profile to load

            # Take a screenshot to debug
            screenshot_path = f"profile_{profile_url.split('/')[-1]}.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"Saved profile screenshot to {screenshot_path}")

            # Extract basic profile information using multiple possible selectors
            name = "N/A"
            headline = "N/A"
            location = "N/A"
            about = "N/A"
            current_position = "N/A"

            # Name - try multiple patterns
            name_patterns = [
                "//h1[@class='text-heading-xlarge inline t-24 v-align-middle break-words']",
                "//h1[contains(@class, 'text-heading-xlarge')]",
                "//h1[contains(@class, 'pv-top-card-section__name')]",
                "//h1",
            ]

            for pattern in name_patterns:
                try:
                    name_element = self.driver.find_element(By.XPATH, pattern)
                    name = name_element.text.strip()
                    if name:
                        break
                except:
                    continue

            # Headline - try multiple patterns
            headline_patterns = [
                "//div[@class='text-body-medium break-words']",
                "//div[contains(@class, 'pv-top-card-section__headline')]",
                "//div[contains(@class, 'text-body-medium')]",
            ]

            for pattern in headline_patterns:
                try:
                    headline_element = self.driver.find_element(By.XPATH, pattern)
                    headline = headline_element.text.strip()
                    if headline:
                        break
                except:
                    continue

            # Location - try multiple patterns
            location_patterns = [
                "//span[@class='text-body-small inline t-black--light break-words']",
                "//span[contains(@class, 'pv-top-card-section__location')]",
                "//span[contains(@class, 'text-body-small') and contains(@class, 'break-words')]",
            ]

            for pattern in location_patterns:
                try:
                    location_element = self.driver.find_element(By.XPATH, pattern)
                    location = location_element.text.strip()
                    if location:
                        break
                except:
                    continue

            # About section - try multiple patterns
            about_patterns = [
                "//div[@class='display-flex ph5 pv3']//span[@aria-hidden='true']",
                "//section[contains(@class, 'pv-about-section')]//p",
                "//div[contains(@class, 'display-flex ph5')]//span[@aria-hidden='true']",
            ]

            for pattern in about_patterns:
                try:
                    about_element = self.driver.find_element(By.XPATH, pattern)
                    about = about_element.text.strip()
                    if about:
                        break
                except:
                    continue

            # Current position - try multiple patterns
            position_patterns = [
                "//section[@id='experience']//li[1]//span[@aria-hidden='true']",
                "//section[contains(@class, 'experience-section')]//li[1]//h3",
                "//section[contains(@id, 'experience')]//li[1]//span[@aria-hidden='true']",
            ]

            for pattern in position_patterns:
                try:
                    position_element = self.driver.find_element(By.XPATH, pattern)
                    current_position = position_element.text.strip()
                    if current_position:
                        break
                except:
                    continue

            # Store the extracted data
            profile_data = {
                "Name": name,
                "Headline": headline,
                "Location": location,
                "About": about,
                "Current Position": current_position,
                "Profile URL": profile_url,
            }

            self.data.append(profile_data)
            print(f"Scraped profile: {name}")

        except Exception as e:
            print(f"Error scraping profile {profile_url}: {e}")

    def save_to_csv(self, filename="linkedin_profiles.csv"):
        """Save the scraped data to a CSV file."""
        if self.data:
            df = pd.DataFrame(self.data)
            df.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print("No data to save.")

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")

    def run(self, search_term, num_pages=3):
        """Run the complete scraping process."""
        try:
            self.setup_driver()
            if self.login():
                self.search_people(search_term, num_pages)
                self.save_to_csv()
            self.close()
        except Exception as e:
            print(f"Error during scraping process: {e}")
            self.close()


if __name__ == "__main__":
    # Get LinkedIn credentials from user input
    EMAIL = input("Enter your LinkedIn email: ")
    PASSWORD = input("Enter your LinkedIn password: ")

    # Initialize and run the scraper
    scraper = LinkedInScraper(EMAIL, PASSWORD)

    # Search term and number of pages to scrape
    SEARCH_TERM = input("Enter search term (e.g., 'founder'): ") or "founder"
    NUM_PAGES = int(input("Enter number of pages to scrape (default: 3): ") or "3")

    scraper.run(SEARCH_TERM, NUM_PAGES)
