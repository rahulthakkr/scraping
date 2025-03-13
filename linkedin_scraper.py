import json
import os
import time

import pandas as pd
import rocketreach
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait


class LinkedInScraper:
    def __init__(self, email, password, rr_api_key=None):
        """Initialize the LinkedIn scraper with login credentials and optional RocketReach API key."""
        self.email = email
        self.password = password
        self.driver = None
        self.data = []
        self.rr_api_key = rr_api_key
        self.rr_client = None
        self.current_profile_name = "N/A"  # Initialize current profile name

        # Initialize RocketReach client if API key is provided
        if self.rr_api_key:
            try:
                self.rr_client = rocketreach.Gateway(api_key=self.rr_api_key)
                print("RocketReach client initialized successfully")
            except Exception as e:
                print(f"Error initializing RocketReach client: {e}")
                self.rr_client = None

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

    def extract_from_search_results(self):
        """Extract profile information directly from search results page."""
        try:
            # Use the existing_names set defined in visit_profiles, or create an empty set if it doesn't exist
            if not hasattr(self, "existing_names"):
                self.existing_names = set()

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

                    # Store the current profile name for use in RocketReach lookup
                    self.current_profile_name = name

                    # Normalize the name for comparison
                    normalized_name = name.strip() if name else "N/A"

                    # Skip if name is in existing_names - do case-insensitive comparison for reliability
                    if any(
                        normalized_name.lower() == existing.lower()
                        for existing in self.existing_names
                    ):
                        print(f"Skipping {normalized_name} - already in CSV file")
                        continue

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

                    # If we have a profile URL, visit the profile to get contact info
                    linkedin_url = None

                    if profile_url != "N/A":
                        # Store current URL to return to search results
                        current_url = self.driver.current_url

                        # Visit profile to get contact info
                        try:
                            self.driver.get(profile_url)
                            time.sleep(3)
                            linkedin_url = self.extract_contact_info_url(profile_url)

                            # Return to search results
                            self.driver.get(current_url)
                            time.sleep(2)
                        except Exception as e:
                            print(f"Error getting contact info for {profile_url}: {e}")
                            # Make sure we return to search results
                            self.driver.get(current_url)
                            time.sleep(2)

                    # Look up additional information from RocketReach if we have a profile URL
                    rr_data = None
                    if self.rr_client:
                        # Use contact info URL if available, otherwise use profile URL
                        lookup_url = linkedin_url if linkedin_url else profile_url
                        if lookup_url != "N/A":
                            rr_data = self.lookup_rocketreach(lookup_url)

                    # Convert RocketReach data to JSON string for storage
                    additional_info = json.dumps(rr_data) if rr_data else "N/A"

                    # Add to data
                    if name != "N/A":
                        profile_data = {
                            "Name": name,
                            "Headline": headline,
                            "Location": location,
                            "About": "N/A",  # Not available in search results
                            "Current Position": headline,  # Using headline as current position
                            "Profile URL": profile_url,
                            "Contact Info URL": linkedin_url if linkedin_url else "N/A",
                            "Additional Info": additional_info,  # Add RocketReach data
                        }
                        self.data.append(profile_data)
                        print(f"Extracted data for {name}")

                except Exception as e:
                    print(f"Error extracting data from search result item: {e}")

        except Exception as e:
            print(f"Error extracting from search results: {e}")

    def lookup_rocketreach(self, linkedin_url):
        """
        Look up a LinkedIn profile on RocketReach to get additional information.

        Args:
            linkedin_url: The LinkedIn profile URL or contact info URL

        Returns:
            Dictionary with RocketReach data or None if lookup failed
        """
        if not self.rr_client:
            print("RocketReach client not initialized. Skipping lookup.")
            return None

        try:
            print(f"Looking up profile on RocketReach: {linkedin_url}")

            # Extract the profile identifier from the URL
            # This handles both vanity URLs and ID-based URLs
            profile_id = None

            # Try to extract the profile ID or username from the URL
            if "/in/" in linkedin_url:
                parts = linkedin_url.split("/in/")
                if len(parts) > 1:
                    profile_id = parts[1].split("?")[0].split("/")[0]
            # Handle contact info URL format: /overlay/contact-info/
            elif "/overlay/contact-info/" in linkedin_url:
                parts = linkedin_url.split("/overlay/contact-info/")
                if len(parts) > 1:
                    profile_id = parts[1].split("?")[0].split("/")[0]

            if not profile_id:
                print(f"Could not extract profile ID from URL: {linkedin_url}")
                return None

            print(f"Extracted profile ID: {profile_id}")

            # Clean the URL to ensure it's in the correct format for RocketReach
            # RocketReach expects URLs in the format: linkedin.com/in/profile-id
            clean_url = f"linkedin.com/in/{profile_id}"

            print(f"Using clean URL for RocketReach lookup: {clean_url}")

            # Perform the lookup
            lookup_result = self.rr_client.person.lookup(linkedin_url=clean_url)

            if hasattr(lookup_result, "person") and lookup_result.person:
                print(f"RocketReach lookup successful for {linkedin_url}")
                print(f"Found data: {lookup_result.person}")
                return lookup_result.person.to_dict()
            else:
                print(f"No RocketReach data found for {linkedin_url}")

                # Try an alternative approach - lookup by name if available
                if (
                    hasattr(self, "current_profile_name")
                    and self.current_profile_name != "N/A"
                ):
                    print(f"Trying to look up by name: {self.current_profile_name}")
                    try:
                        name_lookup = self.rr_client.person.search(
                            name=self.current_profile_name, limit=1
                        )
                        if (
                            hasattr(name_lookup, "people")
                            and name_lookup.people
                            and len(name_lookup.people) > 0
                        ):
                            print(f"Found person by name: {name_lookup.people[0]}")
                            return name_lookup.people[0].to_dict()
                    except Exception as e:
                        print(f"Error looking up by name: {e}")
                        return {}

                return {}

        except Exception as e:
            print(f"Error looking up profile on RocketReach: {e}")
            return None

    def extract_contact_info_url(self, profile_url):
        """
        Click on the 'Contact info' button and extract the contact info URL.

        Args:
            profile_url: The LinkedIn profile URL

        Returns:
            Tuple of (contact_info_url, email, phone, website) or (None, None, None, None) if not found
        """
        try:
            # Make sure we're on the profile page
            if profile_url not in self.driver.current_url:
                self.driver.get(profile_url)
                time.sleep(3)

            # Try different patterns for the contact info button
            contact_info_button = None
            contact_info_patterns = [
                "//a[@id='top-card-text-details-contact-info' and contains(@class, 'ember-view')]",
                "//a[contains(text(), 'Contact info')]",
                "//a[contains(@class, 'link-without-visited-state') and contains(text(), 'Contact info')]",
                "//a[contains(@href, '/overlay/contact-info/')]",
            ]

            for pattern in contact_info_patterns:
                try:
                    contact_info_button = self.driver.find_element(By.XPATH, pattern)
                    if contact_info_button:
                        print(f"Found contact info button using pattern: {pattern}")
                        break
                except:
                    continue

            if not contact_info_button:
                print("Could not find contact info button")
                return None, None, None, None

            # Get the href attribute before clicking
            contact_info_url = contact_info_button.get_attribute("href")
            contact_info_url = contact_info_url.split("con")
            print(f"Contact info URL: {contact_info_url}")

            # Click the button to open contact info overlay
            contact_info_button.click()
            time.sleep(3)  # Wait for overlay to load

            linkedin_url = None
            try:
                linkedin_url = self.driver.find_element(
                    By.XPATH, "//a[contains(@href, 'linkedin.com/in/')]"
                )
                linkedin_url = linkedin_url.get_attribute("href")
            except:
                pass

            # Close the overlay by pressing Escape
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)

            return linkedin_url

        except Exception as e:
            print(f"Error extracting contact info: {e}")
            return None, None, None, None

    def scrape_profile(self, profile_url, already_on_page=False):
        """
        Visit a profile and extract basic information.

        Args:
            profile_url: The LinkedIn profile URL to scrape
            already_on_page: If True, assumes we're already on the profile page
        """
        try:
            if not already_on_page:
                print(f"Visiting profile: {profile_url}")
                self.driver.get(profile_url)
                time.sleep(5)  # Increased wait time for profile to load
            else:
                print(f"Already on profile page: {profile_url}")

            # Extract contact info URL and details
            linkedin_url = self.extract_contact_info_url(profile_url)

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

            # Store the current profile name for use in RocketReach lookup
            self.current_profile_name = name

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

            # Look up additional information from RocketReach
            rr_data = None
            if self.rr_client:
                # Use contact info URL if available, otherwise use profile URL
                lookup_url = linkedin_url if linkedin_url else profile_url
                rr_data = self.lookup_rocketreach(lookup_url)

            # Convert RocketReach data to JSON string for storage
            additional_info = json.dumps(rr_data) if rr_data else "N/A"

            # Store the extracted data
            profile_data = {
                "Name": name,
                "Headline": headline,
                "Location": location,
                "About": about,
                "Current Position": current_position,
                "Profile URL": profile_url,
                "Contact Info URL": linkedin_url if linkedin_url else "N/A",
                "Additional Info": additional_info,  # Add RocketReach data
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
            # Remove duplicate entries based on Profile URL
            unique_data = []
            seen_urls = set()

            for entry in self.data:
                profile_url = entry.get("Profile URL", "")
                if profile_url and profile_url not in seen_urls:
                    unique_data.append(entry)
                    seen_urls.add(profile_url)

            if not unique_data:
                print("No unique data to save after removing duplicates.")
                return

            print(f"Removed {len(self.data) - len(unique_data)} duplicate entries")

            df = pd.DataFrame(unique_data)

            if append and os.path.exists(filename):
                # Check if file exists and has content
                try:
                    # Read existing CSV to check headers and existing entries
                    existing_df = pd.read_csv(filename)

                    # Get existing profile URLs to avoid duplicates
                    existing_urls = set(existing_df["Profile URL"].tolist())

                    # Filter out entries that already exist in the CSV
                    new_entries = df[~df["Profile URL"].isin(existing_urls)]

                    if new_entries.empty:
                        print(f"No new entries to append to {filename}")
                        return

                    print(f"Appending {len(new_entries)} new entries to {filename}")

                    # Append without writing headers
                    new_entries.to_csv(filename, mode="a", header=False, index=False)
                    print(f"Data appended to {filename}")
                except pd.errors.EmptyDataError:
                    # File exists but is empty, write with headers
                    df.to_csv(filename, index=False)
                    print(f"Data saved to {filename} (file was empty)")
            else:
                # Create new file or overwrite existing
                df.to_csv(filename, index=False)
                print(f"Data saved to {filename}")

            # Update self.data to contain only unique entries
            self.data = unique_data
        else:
            print("No data to save.")

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed.")

    def visit_profiles(self, search_term, num_profiles=5):
        """
        Search for people with the given search term and visit up to the requested number of profiles.
        Skip profiles that are already in the CSV file. Will automatically navigate to next pages
        as needed until reaching the requested number of new profiles.

        Args:
            search_term: The keyword to search for on LinkedIn
            num_profiles: Maximum number of profiles to visit
        """
        try:
            # Navigate to LinkedIn search page for people
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_term.replace(' ', '%20')}"
            self.driver.get(search_url)
            time.sleep(10)  # Wait time for page to load

            print(f"Searching for '{search_term}' on LinkedIn...")
            print(
                f"Will visit up to {num_profiles} unique profiles, automatically navigating through pages as needed"
            )

            # Create filename for this search
            filename = f"linkedin_profiles_{search_term.replace(' ', '_')}.csv"

            # Check if the CSV file already exists and load existing names
            self.existing_names = set()
            if os.path.exists(filename):
                try:
                    existing_df = pd.read_csv(filename)
                    if "Name" in existing_df.columns:
                        # Normalize names: strip whitespace and convert to lowercase for better matching
                        normalized_names = [
                            name.strip()
                            for name in existing_df["Name"].tolist()
                            if isinstance(name, str)
                        ]
                        self.existing_names = set(normalized_names)
                        print(
                            f"Found {len(self.existing_names)} existing profiles in CSV. Will skip these names."
                        )
                except Exception as e:
                    print(f"Error reading existing CSV: {e}")

            # Initialize counters
            profiles_visited = 0
            current_page = 1
            max_empty_pages = (
                3  # Stop after this many consecutive pages with no new profiles
            )

            # Track consecutive pages with no new profiles
            consecutive_empty_pages = 0

            # Continue until we've visited enough profiles
            while profiles_visited < num_profiles:
                print(f"\n--- Processing search results page {current_page} ---")

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
                    links5 = self.driver.find_elements(
                        By.CSS_SELECTOR, "a[href*='/in/']"
                    )
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
                print(
                    f"Found {len(profile_urls)} unique profile URLs on page {current_page}"
                )

                # # Print the first few URLs for debugging
                # for i, url in enumerate(profile_urls[:3]):
                #     print(f"URL {i + 1}: {url}")

                # If no profiles found, try to extract information directly from search results
                if len(profile_urls) == 0:
                    print(
                        "No profile links found. Attempting to extract data directly from search results..."
                    )
                    self.extract_from_search_results()
                    # Save the data extracted from search results
                    self.save_to_csv(filename, append=(profiles_visited > 0))

                    # If still no data, try a different approach
                    if not self.data:
                        print(
                            "Still no data found. Trying alternative extraction method..."
                        )
                        self.extract_from_search_results_alternative()
                        self.save_to_csv(filename, append=(profiles_visited > 0))
                else:
                    # Calculate how many more profiles we need to visit
                    profiles_remaining = num_profiles - profiles_visited

                    # Limit to the number of profiles we still need
                    profile_urls = profile_urls[:profiles_remaining]

                    # Visit each profile and extract data
                    for url in profile_urls:
                        # Clean the URL to remove query parameters
                        clean_url = url.split("?")[0]

                        # Check if we need to get the name from the profile before deciding to skip
                        # This requires visiting the profile page to see the name
                        try:
                            # Visit the profile page to get the name
                            self.driver.get(clean_url)
                            time.sleep(5)

                            # Extract the name using EXACTLY the same patterns from scrape_profile method
                            # This ensures we get the same name that would eventually be stored in the CSV
                            name = "N/A"
                            name_patterns = [
                                "//h1[@class='text-heading-xlarge inline t-24 v-align-middle break-words']",
                                "//h1[contains(@class, 'text-heading-xlarge')]",
                                "//h1[contains(@class, 'pv-top-card-section__name')]",
                                "//h1",
                            ]

                            for pattern in name_patterns:
                                try:
                                    name_element = self.driver.find_element(
                                        By.XPATH, pattern
                                    )
                                    name = name_element.text.strip()
                                    if name:
                                        break
                                except:
                                    continue

                            # Normalize the name for comparison
                            normalized_name = name.strip() if name else "N/A"

                            # Skip if name is in existing_names - do case-insensitive comparison for reliability
                            if any(
                                normalized_name.lower() == existing.lower()
                                for existing in self.existing_names
                            ):
                                print(
                                    f"Skipping {normalized_name} - already in CSV file"
                                )
                                # Return to search results page
                                self.driver.back()
                                time.sleep(5)  # Wait for page to load
                                continue

                            # Store the current data length
                            previous_data_length = len(self.data)

                            # Since we're already on the profile page, just scrape it directly
                            self.scrape_profile(clean_url, already_on_page=True)

                            # Only increment visits count if new data was added
                            if len(self.data) > previous_data_length:
                                profiles_visited += 1
                                print(
                                    f"Successfully visited profile {profiles_visited} of {num_profiles}"
                                )

                            # Save only the newly added data
                            if len(self.data) > previous_data_length:
                                # Always append to the file if it exists
                                self.save_to_csv(filename, append=True)
                            else:
                                print(
                                    f"Warning: No new data was added for profile {clean_url}"
                                )

                            # Return to search results page
                            self.driver.back()
                            time.sleep(5)  # Wait for page to load

                            # If we've visited the requested number of profiles, break
                            if profiles_visited >= num_profiles:
                                break

                        except Exception as e:
                            print(f"Error scraping profile {clean_url}: {e}")

                # Check if we found any new profiles on this page
                new_profiles_on_page = len(profile_urls) > 0

                # If no new profiles were found on this page, increment the empty page counter
                if not new_profiles_on_page:
                    consecutive_empty_pages += 1
                    print(f"No new profiles found on page {current_page}")
                else:
                    # Reset the counter if we found profiles
                    consecutive_empty_pages = 0

                # If we've visited enough profiles, break out of the loop
                if profiles_visited >= num_profiles:
                    print(
                        f"Reached the target of {num_profiles} profiles. Stopping search."
                    )
                    break

                # If we've gone through too many pages with no new profiles, stop
                if consecutive_empty_pages >= max_empty_pages:
                    print(
                        f"No new profiles found on {consecutive_empty_pages} consecutive pages. Stopping search."
                    )
                    break

                # Try to find and click the next page button
                next_page_found = False
                next_button_patterns = [
                    "//button[@aria-label='Next']",
                    "//button[contains(@class, 'artdeco-pagination__button--next')]",
                    "//button[contains(text(), 'Next') or .//span[contains(text(), 'Next')]]",
                    "//button[.//li-icon[@type='chevron-right-icon']]",
                ]
                while not next_page_found:
                    for _ in range(2):  # in the second we add scrolling
                        for pattern in next_button_patterns:
                            try:
                                next_button = self.driver.find_element(
                                    By.XPATH, pattern
                                )
                                if next_button and next_button.is_enabled():
                                    print(
                                        f"Found 'Next' button with pattern {pattern}. Clicking..."
                                    )
                                    next_button.click()
                                    next_page_found = True
                                    time.sleep(5)  # Wait for page to load
                                    break
                            except Exception as e:
                                print(
                                    f"Error finding 'Next' button with pattern {pattern}: {e}"
                                )
                                continue
                        try:
                            print("Scrolling to bottom of page...")
                            self.driver.execute_script(
                                "window.scrollTo(0, document.body.scrollHeight);"
                            )
                            time.sleep(3)
                        except Exception as e:
                            print(
                                f"Error while scrolling or finding page number buttons: {e}"
                            )
                            continue

                # We reach here after scrolling to the bottom of the page

                # Pattern 5: Try pagination using buttons with numbers
                pagination_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@class, 'artdeco-pagination__button') and not(contains(@class, 'selected'))]",
                )

                for button in pagination_buttons:
                    try:
                        button_text = button.text.strip()
                        if (
                            button_text
                            and button_text.isdigit()
                            and int(button_text) == current_page + 1
                        ):
                            print(
                                f"Found page number button for page {button_text}. Clicking..."
                            )
                            button.click()
                            next_page_found = True
                            time.sleep(5)
                            break
                    except:
                        continue

                # Try modifying the URL as a last resort
                if not next_page_found:
                    try:
                        current_url = self.driver.current_url
                        if "page=" in current_url:
                            # URL already has pagination parameter
                            new_url = current_url.replace(
                                f"page={current_page}", f"page={current_page + 1}"
                            )
                        else:
                            # Add pagination parameter
                            if "?" in current_url:
                                new_url = f"{current_url}&page={current_page + 1}"
                            else:
                                new_url = f"{current_url}?page={current_page + 1}"

                        print(f"Trying URL-based pagination: {new_url}")
                        self.driver.get(new_url)
                        time.sleep(5)

                        # Check if we actually got to a new page
                        if (
                            "page=" in self.driver.current_url
                            and f"page={current_page + 1}" in self.driver.current_url
                        ):
                            next_page_found = True
                            print("URL-based pagination successful")
                    except Exception as e:
                        print(f"Error during URL-based pagination: {e}")

                if next_page_found:
                    current_page += 1
                    print(f"Successfully navigated to page {current_page}")
                else:
                    print("Could not find a 'Next' button. Ending search.")
                    break

            print(
                f"Successfully visited {profiles_visited} profiles across {current_page} pages"
            )

            # Final save to ensure all data is saved
            if self.data:
                self.save_to_csv(filename, append=True)
            else:
                print("No data was collected during the scraping process.")

        except Exception as e:
            print(f"Error during profile visits: {e}")
            # Save any data collected so far
            if self.data:
                self.save_to_csv(filename, append=True)

    def debug_page_source(self, filename):
        """Save the current page source to a file for debugging."""
        try:
            page_source = self.driver.page_source
            with open(filename, "w", encoding="utf-8") as f:
                f.write(page_source)
            print(f"Saved page source to {filename}")
        except Exception as e:
            print(f"Error saving page source: {e}")
