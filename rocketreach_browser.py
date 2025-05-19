import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
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

        # Mobile Emulation DISABLED
        # mobile_emulation = {
        #     "deviceMetrics": {"width": 393, "height": 851, "pixelRatio": 3.0},
        #     "userAgent": "Mozilla/5.0 (Linux; Android 13; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"
        # }
        # chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

        # Restore standard desktop options
        chrome_options.add_argument("--start-maximized")  # Start maximized
        chrome_options.add_argument("--disable-notifications")  # Disable notifications
        chrome_options.add_argument("--window-size=1280,800")  # Ensure reasonable size

        # Initialize Chrome WebDriver with options
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Log in to RocketReach."""
        try:
            # Proceed with normal form login if cookie login
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
                # if recaptcha:
                #     print("CAPTCHA detected! You may need to manually solve it.")
                #     # Give user time to solve CAPTCHA if needed
                #     input("Press Enter after you've solved the CAPTCHA (if needed)...")
            except NoSuchElementException:
                # No CAPTCHA or it's already handled
                pass

            # Click login button
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
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

    def get_contact_email(self, linkedin_url):
        """Navigate to RocketReach person page, click 'Get Contact Info' using JS, and return email."""
        # Encode slashes in LinkedIn URL for RocketReach query param
        encoded_link = linkedin_url.replace("/", "%2F")
        url = f"https://rocketreach.co/person?start=1&pageSize=10&link={encoded_link}"
        self.driver.get(url)
        # Allow some time for initial page load before executing script
        time.sleep(5)

        # Debug: Print page title and URL to ensure we're on the right page
        print(f"Page loaded. Title: {self.driver.title}")
        print(f"Current URL: {self.driver.current_url}")

        # --- JavaScript Click Logic ---
        # Refined script focusing on the specific button structure
        js_click_script = r"""
        return (async () => {
            var callback = arguments[arguments.length - 1];
            var clicked = false;
            var logMessages = [];

            logMessages.push('Looking for span[data-onboarding-id="get-contact-button"]...');
            // Try finding the specific span first
            var targetSpan = document.querySelector('span[data-onboarding-id="get-contact-button"]');

            if (!targetSpan) {
                logMessages.push('Span with data-onboarding-id="get-contact-button" not found.');
            } else {
                logMessages.push('Span found. Looking for button inside...');
                // Look for a button, prioritizing common classes if needed, otherwise any button
                var button = targetSpan.querySelector('button.button-primary') || targetSpan.querySelector('button');

                if (!button) {
                    logMessages.push('Button not found within the target span.');
                } else {
                    logMessages.push('Button found within span. Text: "' + (button.textContent || button.innerText || '').trim() + '". Checking visibility...');

                    // Robust visibility check
                    var rect = button.getBoundingClientRect();
                    var computedStyle = window.getComputedStyle(button);
                    var isVisible = (
                        rect.width > 0 &&
                        rect.height > 0 &&
                        computedStyle.visibility !== 'hidden' &&
                        computedStyle.display !== 'none' &&
                        computedStyle.opacity !== '0' &&
                        button.offsetParent !== null // Check if it's part of the layout
                    );

                    logMessages.push('Button visibility: ' + isVisible);

                    if (isVisible) {
                        logMessages.push('Attempting to click visible button...');
                        try {
                            button.scrollIntoView({ block: 'center', inline: 'center' });
                            await new Promise(resolve => setTimeout(resolve, 200)); // Slightly longer delay after scroll

                            // Attempt 1: Standard click
                            button.click();
                            clicked = true;
                            logMessages.push('Standard click successful.');

                        } catch (e1) {
                            logMessages.push('Standard click failed: ' + e1.message + '. Trying dispatchEvent...');
                            try {
                                // Attempt 2: Dispatch MouseEvent
                                var clickEvent = new MouseEvent('click', {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true
                                });
                                button.dispatchEvent(clickEvent);
                                clicked = true; // Assume success if dispatch doesn't error immediately
                                logMessages.push('dispatchEvent click successful.');
                            } catch (e2) {
                                logMessages.push('dispatchEvent click also failed: ' + e2.message);
                                clicked = false; // Definitely failed
                            }
                        }
                    } else {
                        logMessages.push('Button found but determined to be not visible.');
                    }
                }
            }

            if (!clicked) {
                logMessages.push('Button click was not successful.');
            }

            console.log(logMessages.join('\n'));
            callback(clicked);
        })();
        """

        email = None
        try:
            print(
                "Executing JavaScript to find and click the visible 'Get Contact Info' button..."
            )
            # Ensure page is fully loaded - increase wait time slightly before script exec
            WebDriverWait(self.driver, 20).until(  # Increased wait to 20s
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Set script timeout for async script
            self.driver.set_script_timeout(30)  # Allow 30s for the async script itself

            # Execute the script using execute_async_script
            click_performed = self.driver.execute_async_script(js_click_script)

            if click_performed:
                print(
                    "JavaScript reported a click was performed. Waiting for email to appear..."
                )
                # Wait longer for the email element to potentially load after the JS click
                try:
                    email_element = WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                # Combined selector for potential email links
                                "a[data-testid='email-phone-text-mobile'], a[href^='mailto:']",
                            )
                        )
                    )
                    email = email_element.text.strip()
                    if not email or "@" not in email:
                        print(
                            "Email element found but no valid email address extracted."
                        )
                        email = None
                    else:
                        print(f"Successfully extracted email: {email}")
                except TimeoutException:
                    print("Email element not found after JavaScript click (timed out).")
                except Exception as e:
                    print(f"Error extracting email after JavaScript click: {e}")
            else:
                print(
                    "JavaScript execution finished, but reported that no visible button was clicked."
                )

        except Exception as e:
            print(
                f"Error during JavaScript execution or subsequent email extraction: {e}"
            )

        # --- End JavaScript Click Logic ---

        # Debugging and final return
        if email:
            return email
        else:
            # Add more info to the failure message
            print(
                "Failed to extract email using JavaScript click method. Check browser console for detailed logs from the script."
            )
            # Save screenshot if we failed to get email
            page_snippet = self.driver.page_source[:1000]  # Increased snippet size
            print(f"Page source snippet (first 1000 chars): {page_snippet}")
            try:
                screenshot_path = "debug_screenshot.png"
                self.driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to {screenshot_path} for debugging.")
            except Exception as e:
                print(f"Error saving screenshot: {e}")
            return None

    def close_driver(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            print("Browser closed.")


# Example Usage (optional)
if __name__ == "__main__":
    # Create an instance of the browser automation class
    rr_browser = RocketReachBrowser()

    # Set up the driver
    rr_browser.setup_driver()

    # Log in
    if rr_browser.login():
        # LinkedIn URL to search for
        linkedin_url = "https://www.linkedin.com/in/shreya-rajpal/"  # Example

        # Get the contact email
        email = rr_browser.get_contact_email(linkedin_url)

        if email:
            print(f"\nSuccessfully retrieved email: {email}")
        else:
            print("\nCould not retrieve email.")

    # Close the browser
    rr_browser.close_driver()
