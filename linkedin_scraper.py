import os
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

                # Pattern 2: Alternative pattern for app-aware links
                try:
                    links2 = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(@class, 'app-aware-link') and contains(@href, '/in/')]",
                    )
                    profile_links.extend(links2)
                    print(f"Found {len(links2)} links with pattern 2")
                except:
                    pass

                # Pattern 3: New pattern based on the provided HTML
                try:
                    links3 = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(@class, 'qWdktykoofflQLeAqgrGCGVRzijLcViJI') and contains(@href, '/in/')]",
                    )
                    profile_links.extend(links3)
                    print(f"Found {len(links3)} links with pattern 3")
                except:
                    pass

                # Pattern 4: Another alternative
                try:
                    links4 = self.driver.find_elements(
                        By.CSS_SELECTOR, "a.search-result__result-link"
                    )
                    profile_links.extend(links4)
                    print(f"Found {len(links4)} links with pattern 4")
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

                # If no profiles found, try to extract information directly from search results
                if len(profile_urls) == 0:
                    print(
                        "No profile links found. Attempting to extract data directly from search results..."
                    )
                    self.extract_from_search_results()
                else:
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

    def extract_from_search_results(self):
        """Extract profile information directly from search results page."""
        try:
            # Find all search result items
            result_items = self.driver.find_elements(
                By.XPATH, "//li[contains(@class, 'sPyyoaQOsCzibiZXNZiIPsQlDbqJU')]"
            )

            if not result_items:
                result_items = self.driver.find_elements(
                    By.XPATH,
                    "//li[contains(@class, 'reusable-search__result-container')]",
                )

            print(f"Found {len(result_items)} search result items")

            for item in result_items:
                try:
                    # Extract data from each result item
                    name = "N/A"
                    headline = "N/A"
                    location = "N/A"
                    profile_url = "N/A"

                    # Name
                    try:
                        name_elem = item.find_element(
                            By.XPATH,
                            ".//span[contains(@class, 'eBNwISpkdUDmzjnfMDCWRdcdBzYMwLkYdI')]/a",
                        )
                        name = name_elem.text.strip()
                        profile_url = name_elem.get_attribute("href")
                    except:
                        try:
                            name_elem = item.find_element(
                                By.XPATH,
                                ".//span[contains(@class, 'entity-result__title-text')]/a",
                            )
                            name = name_elem.text.strip()
                            profile_url = name_elem.get_attribute("href")
                        except:
                            pass

                    # Headline
                    try:
                        headline_elem = item.find_element(
                            By.XPATH,
                            ".//div[contains(@class, 'FBhjEoyAzmTuyITebnedTzGaSyYHjnEDsjUEY')]",
                        )
                        headline = headline_elem.text.strip()
                    except:
                        try:
                            headline_elem = item.find_element(
                                By.XPATH,
                                ".//div[contains(@class, 'entity-result__primary-subtitle')]",
                            )
                            headline = headline_elem.text.strip()
                        except:
                            pass

                    # Location
                    try:
                        location_elem = item.find_element(
                            By.XPATH,
                            ".//div[contains(@class, 'AZoaSfcPFEqGecZFTogUQbRlYXHDrBLqvghsY')]",
                        )
                        location = location_elem.text.strip()
                    except:
                        try:
                            location_elem = item.find_element(
                                By.XPATH,
                                ".//div[contains(@class, 'entity-result__secondary-subtitle')]",
                            )
                            location = location_elem.text.strip()
                        except:
                            pass

                    # Add to data
                    if name != "N/A":
                        profile_data = {
                            "Name": name,
                            "Headline": headline,
                            "Location": location,
                            "About": "N/A",  # Not available in search results
                            "Current Position": headline,  # Using headline as current position
                            "Profile URL": profile_url,
                        }
                        self.data.append(profile_data)
                        print(f"Extracted data for {name}")

                except Exception as e:
                    print(f"Error extracting data from search result item: {e}")

        except Exception as e:
            print(f"Error extracting from search results: {e}")

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
            skills = "N/A"
            investments = "N/A"

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

            # Extract angel investor specific information
            self.extract_investor_info(profile_url)

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

    def extract_investor_info(self, profile_url):
        """Extract angel investor specific information like skills and investments."""
        try:
            # Check if we're already on the profile page, if not navigate to it
            if profile_url not in self.driver.current_url:
                self.driver.get(profile_url)
                time.sleep(3)

            # Extract skills
            skills = []
            try:
                # Try to find the skills section
                # First check if we need to click to see skills
                skills_buttons = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, '/details/skills/')]"
                )
                if skills_buttons:
                    # Click to view skills
                    skills_buttons[0].click()
                    time.sleep(2)

                    # Extract skills from the modal
                    skill_elements = self.driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'skill-category-entity__name')]",
                    )
                    for skill in skill_elements:
                        skills.append(skill.text.strip())

                    # Close the modal
                    close_button = self.driver.find_element(
                        By.XPATH, "//button[@aria-label='Dismiss']"
                    )
                    close_button.click()
                    time.sleep(1)
                else:
                    # Try to extract skills directly from the profile
                    skill_elements = self.driver.find_elements(
                        By.XPATH,
                        "//span[contains(@class, 'pv-skill-category-entity__name-text')]",
                    )
                    for skill in skill_elements:
                        skills.append(skill.text.strip())
            except Exception as e:
                print(f"Error extracting skills: {e}")

            # Extract investment information
            investments = []
            try:
                # Look for sections that might contain investment information
                sections = self.driver.find_elements(
                    By.XPATH, "//section[contains(@class, 'pv-profile-section')]"
                )

                for section in sections:
                    section_title = (
                        section.find_element(By.XPATH, ".//h2").text.strip().lower()
                    )
                    if (
                        "investment" in section_title
                        or "venture" in section_title
                        or "portfolio" in section_title
                    ):
                        # Extract investment items
                        investment_items = section.find_elements(By.XPATH, ".//li")
                        for item in investment_items:
                            investments.append(item.text.strip())
            except Exception as e:
                print(f"Error extracting investments: {e}")

            # Add to profile data
            if self.data and self.data[-1]["Profile URL"] == profile_url:
                self.data[-1]["Skills"] = ", ".join(skills) if skills else "N/A"
                self.data[-1]["Investments"] = (
                    ", ".join(investments) if investments else "N/A"
                )

        except Exception as e:
            print(f"Error extracting investor info: {e}")

    def save_to_csv(self, filename="linkedin_profiles.csv", append=False):
        """Save the scraped data to a CSV file.

        Args:
            filename: Name of the CSV file
            append: If True, append to existing file; if False, overwrite
        """
        if self.data:
            df = pd.DataFrame(self.data)

            if append and os.path.exists(filename):
                # Check if file exists and has content
                try:
                    # Read existing CSV to check headers
                    existing_df = pd.read_csv(filename)

                    # Append without writing headers
                    df.to_csv(filename, mode="a", header=False, index=False)
                    print(f"Data appended to {filename}")
                except pd.errors.EmptyDataError:
                    # File exists but is empty, write with headers
                    df.to_csv(filename, index=False)
                    print(f"Data saved to {filename} (file was empty)")
            else:
                # Create new file or overwrite existing
                df.to_csv(filename, index=False)
                print(f"Data saved to {filename}")
        else:
            print("No data to save.")

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")

    def run(self, search_term, num_profiles=5):
        """Run the complete scraping process."""
        try:
            self.setup_driver()
            if self.login():
                print(f"Searching for '{search_term}' on LinkedIn...")
                print(f"Will visit up to {num_profiles} profiles.")
                print("This may take a few minutes. Please wait...")

                # Use visit_profiles instead of search_people
                self.visit_profiles(search_term, num_profiles)

                # No need to save to CSV here as visit_profiles already does this
                filename = f"linkedin_profiles_{search_term.replace(' ', '_')}.csv"
                print("\nScraping completed successfully!")
                print(f"Check '{filename}' for the extracted profile information.")
            self.close()
        except Exception as e:
            print(f"Error during scraping process: {e}")
            self.close()

    def visit_profiles(self, search_term, num_profiles=5):
        """Search for people with the given search term and visit up to the requested number of profiles."""
        try:
            # Navigate to LinkedIn search page for people
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_term.replace(' ', '%20')}"
            self.driver.get(search_url)
            time.sleep(5)  # Wait time for page to load

            print(f"Searching for '{search_term}' on LinkedIn...")

            # Create filename for this search
            filename = f"linkedin_profiles_{search_term.replace(' ', '_')}.csv"

            # Take a screenshot to debug
            screenshot_path = "search_page.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")

            # Save page source for debugging
            self.debug_page_source("search_page_source.html")
            print("Saved page source for debugging")

            # Try different XPath patterns for profile links
            profile_links = []

            # Pattern 1: Standard entity-result pattern
            try:
                links1 = self.driver.find_elements(
                    By.XPATH, "//span[@class='entity-result__title-text']/a"
                )
                profile_links.extend(links1)
                print(f"Found {len(links1)} links with pattern 1")
            except Exception as e:
                print(f"Error with pattern 1: {e}")

            # Pattern 2: Alternative pattern for app-aware links
            try:
                links2 = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@class, 'app-aware-link') and contains(@href, '/in/')]",
                )
                profile_links.extend(links2)
                print(f"Found {len(links2)} links with pattern 2")
            except Exception as e:
                print(f"Error with pattern 2: {e}")

            # Pattern 3: New pattern based on the provided HTML
            try:
                links3 = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@class, 'qWdktykoofflQLeAqgrGCGVRzijLcViJI') and contains(@href, '/in/')]",
                )
                profile_links.extend(links3)
                print(f"Found {len(links3)} links with pattern 3")
            except Exception as e:
                print(f"Error with pattern 3: {e}")

            # Pattern 4: Another pattern from the provided HTML
            try:
                links4 = self.driver.find_elements(
                    By.XPATH,
                    "//span[contains(@class, 'eBNwISpkdUDmzjnfMDCWRdcdBzYMwLkYdI')]/a",
                )
                profile_links.extend(links4)
                print(f"Found {len(links4)} links with pattern 4")
            except Exception as e:
                print(f"Error with pattern 4: {e}")

            # Pattern 5: Try a more generic approach with CSS selectors
            try:
                links5 = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/in/']")
                profile_links.extend(links5)
                print(f"Found {len(links5)} links with pattern 5 (generic href)")
            except Exception as e:
                print(f"Error with pattern 5: {e}")

            # Pattern 6: Try finding search result containers first
            try:
                result_containers = self.driver.find_elements(
                    By.XPATH,
                    "//li[contains(@class, 'reusable-search__result-container')]",
                )
                print(f"Found {len(result_containers)} result containers")

                for container in result_containers:
                    try:
                        link = container.find_element(
                            By.XPATH, ".//a[contains(@href, '/in/')]"
                        )
                        profile_links.append(link)
                    except:
                        pass
                print(f"Found {len(profile_links)} links from result containers")
            except Exception as e:
                print(f"Error finding result containers: {e}")

            # Extract the href attributes
            profile_urls = []
            for link in profile_links:
                try:
                    url = link.get_attribute("href")
                    if url and "/in/" in url:
                        profile_urls.append(url)
                except Exception as e:
                    print(f"Error extracting href: {e}")
                    continue

            # Remove duplicates
            profile_urls = list(set(profile_urls))
            print(f"Found {len(profile_urls)} unique profile URLs")

            # Print the first few URLs for debugging
            for i, url in enumerate(profile_urls[:3]):
                print(f"URL {i + 1}: {url}")

            # If no profiles found, try to extract information directly from search results
            if len(profile_urls) == 0:
                print(
                    "No profile links found. Attempting to extract data directly from search results..."
                )
                self.extract_from_search_results()
                # Save the data extracted from search results
                self.save_to_csv(filename)

                # If still no data, try a different approach
                if not self.data:
                    print(
                        "Still no data found. Trying alternative extraction method..."
                    )
                    self.extract_from_search_results_alternative()
                    self.save_to_csv(filename)
                return

            # Limit to the requested number of profiles
            profile_urls = profile_urls[:num_profiles]
            profiles_visited = 0

            # Visit each profile and extract data
            for url in profile_urls:
                # Clean the URL to remove query parameters
                clean_url = url.split("?")[0]

                try:
                    # Store the current data length
                    previous_data_length = len(self.data)

                    self.scrape_profile(clean_url)
                    profiles_visited += 1
                    print(
                        f"Successfully visited profile {profiles_visited} of {num_profiles}"
                    )

                    # Save only the newly added data
                    if len(self.data) > previous_data_length:
                        # For the first profile, create a new file
                        append_mode = profiles_visited > 1
                        self.save_to_csv(filename, append=append_mode)
                    else:
                        print(f"Warning: No new data was added for profile {clean_url}")

                    # Return to search results page
                    self.driver.back()
                    time.sleep(3)  # Wait for page to load

                    # If we've visited the requested number of profiles, break
                    if profiles_visited >= num_profiles:
                        break

                except Exception as e:
                    print(f"Error scraping profile {clean_url}: {e}")

            print(f"Successfully visited {profiles_visited} profiles")

            # Final save to ensure all data is saved
            if self.data:
                self.save_to_csv(filename)
            else:
                print("No data was collected during the scraping process.")

        except Exception as e:
            print(f"Error during profile visits: {e}")

    def extract_from_search_results_alternative(self):
        """Alternative method to extract profile information from search results page."""
        try:
            print("Using alternative extraction method...")

            # Try to find any elements that might contain profile information
            # Look for any list items that might be search results
            list_items = self.driver.find_elements(By.TAG_NAME, "li")
            print(f"Found {len(list_items)} list items")

            for item in list_items:
                try:
                    # Try to find a link that might be a profile
                    links = item.find_elements(By.TAG_NAME, "a")
                    profile_url = None

                    for link in links:
                        href = link.get_attribute("href")
                        if href and "/in/" in href:
                            profile_url = href
                            break

                    if not profile_url:
                        continue

                    # Try to find name, headline, and location
                    name = "N/A"
                    headline = "N/A"
                    location = "N/A"

                    # Look for text elements
                    text_elements = item.find_elements(By.TAG_NAME, "span")
                    if len(text_elements) > 0:
                        name = text_elements[0].text.strip() or "N/A"

                    if len(text_elements) > 1:
                        headline = text_elements[1].text.strip() or "N/A"

                    if len(text_elements) > 2:
                        location = text_elements[2].text.strip() or "N/A"

                    # Add to data if we have at least a name and profile URL
                    if name != "N/A" and profile_url:
                        profile_data = {
                            "Name": name,
                            "Headline": headline,
                            "Location": location,
                            "About": "N/A",
                            "Current Position": headline,
                            "Profile URL": profile_url,
                            "Skills": "N/A",
                            "Investments": "N/A",
                        }
                        self.data.append(profile_data)
                        print(f"Extracted data for {name}")
                except Exception:
                    continue

            print(f"Alternative extraction found {len(self.data)} profiles")

        except Exception as e:
            print(f"Error in alternative extraction: {e}")

    def debug_page_source(self, filename):
        """Save the current page source to a file for debugging."""
        try:
            page_source = self.driver.page_source
            with open(filename, "w", encoding="utf-8") as f:
                f.write(page_source)
            print(f"Saved page source to {filename}")
        except Exception as e:
            print(f"Error saving page source: {e}")

    def extract_first_from_search_results(self):
        """Extract profile information directly from the first search result."""
        try:
            # Find the first search result item
            result_item = None

            try:
                result_item = self.driver.find_element(
                    By.XPATH, "//li[contains(@class, 'sPyyoaQOsCzibiZXNZiIPsQlDbqJU')]"
                )
            except:
                pass

            if not result_item:
                try:
                    result_item = self.driver.find_element(
                        By.XPATH,
                        "//li[contains(@class, 'reusable-search__result-container')]",
                    )
                except:
                    pass

            if result_item:
                print("Found a search result item")

                # Extract data from the result item
                name = "N/A"
                headline = "N/A"
                location = "N/A"
                profile_url = "N/A"

                # Name
                try:
                    name_elem = result_item.find_element(
                        By.XPATH,
                        ".//span[contains(@class, 'eBNwISpkdUDmzjnfMDCWRdcdBzYMwLkYdI')]/a",
                    )
                    name = name_elem.text.strip()
                    profile_url = name_elem.get_attribute("href")
                except:
                    try:
                        name_elem = result_item.find_element(
                            By.XPATH,
                            ".//span[contains(@class, 'entity-result__title-text')]/a",
                        )
                        name = name_elem.text.strip()
                        profile_url = name_elem.get_attribute("href")
                    except:
                        pass

                # Headline
                try:
                    headline_elem = result_item.find_element(
                        By.XPATH,
                        ".//div[contains(@class, 'FBhjEoyAzmTuyITebnedTzGaSyYHjnEDsjUEY')]",
                    )
                    headline = headline_elem.text.strip()
                except:
                    try:
                        headline_elem = result_item.find_element(
                            By.XPATH,
                            ".//div[contains(@class, 'entity-result__primary-subtitle')]",
                        )
                        headline = headline_elem.text.strip()
                    except:
                        pass

                # Location
                try:
                    location_elem = result_item.find_element(
                        By.XPATH,
                        ".//div[contains(@class, 'AZoaSfcPFEqGecZFTogUQbRlYXHDrBLqvghsY')]",
                    )
                    location = location_elem.text.strip()
                except:
                    try:
                        location_elem = result_item.find_element(
                            By.XPATH,
                            ".//div[contains(@class, 'entity-result__secondary-subtitle')]",
                        )
                        location = location_elem.text.strip()
                    except:
                        pass

                # Add to data
                if name != "N/A":
                    profile_data = {
                        "Name": name,
                        "Headline": headline,
                        "Location": location,
                        "About": "N/A",  # Not available in search results
                        "Current Position": headline,  # Using headline as current position
                        "Profile URL": profile_url,
                        "Skills": "N/A",  # Not available in search results
                        "Investments": "N/A",  # Not available in search results
                    }
                    self.data.append(profile_data)
                    print(f"Extracted data for {name}")
            else:
                print("No search result items found")

        except Exception as e:
            print(f"Error extracting from search results: {e}")


if __name__ == "__main__":
    # Get LinkedIn credentials from user input
    EMAIL = input("Enter your LinkedIn email: ")
    PASSWORD = input("Enter your LinkedIn password: ")

    # Initialize and run the scraper
    scraper = LinkedInScraper(EMAIL, PASSWORD)

    # Search term and number of profiles to scrape
    SEARCH_TERM = (
        input("Enter search term (e.g., 'angel investor'): ") or "angel investor"
    )
    NUM_PROFILES = int(
        input("Enter number of profiles to scrape (default: 5): ") or "5"
    )

    scraper.run(SEARCH_TERM, NUM_PROFILES)
