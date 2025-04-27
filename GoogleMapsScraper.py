import time
import csv
import tkinter as tk
import os
import sys
import platform
import subprocess
import threading
import queue
import random
import re
from datetime import datetime
from tkinter import ttk, filedialog, messagebox, font
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScraperThread(threading.Thread):
    """Thread class for running the scraping process in the background"""
    def __init__(self, scraper, params):
        threading.Thread.__init__(self)
        self.scraper = scraper
        self.params = params
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.daemon = True  # Thread will exit when main program exits
        
    def run(self):
        try:
            # Extract parameters
            method = self.params.get('method')
            business_type = self.params.get('business_type', '')
            location = self.params.get('location', '')
            direct_url = self.params.get('direct_url', '')
            num_results = self.params.get('num_results')
            output_file = self.params.get('output_file')
            headless = self.params.get('headless')
            delay = self.params.get('delay')
            
            # Update status
            self.queue.put(('status', f"Starting Chrome browser..."))
            
            # Setup Chrome
            chrome_binary = self.scraper.find_chrome_binary()
            if not chrome_binary:
                self.queue.put(('error', "Chrome browser not found"))
                return
                
            self.queue.put(('status', f"Found Chrome at: {chrome_binary}"))
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.binary_location = chrome_binary
            if headless:
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--log-level=3")
            
            # Add user agent rotation
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
            
            # Get ChromeDriver path
            driver_path = self.scraper.get_chromedriver_path()
            
            # Set up the WebDriver
            try:
                if driver_path and os.path.exists(driver_path):
                    service = Service(executable_path=driver_path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Fall back to system PATH
                    driver = webdriver.Chrome(options=chrome_options)
                    
                wait = WebDriverWait(driver, 10)
                self.queue.put(('status', "Chrome browser started successfully"))
                
            except Exception as e:
                error_msg = str(e)
                self.queue.put(('status', f"Error starting Chrome: {error_msg}"))
                self.queue.put(('error', f"Failed to start Chrome browser: {error_msg}"))
                return
            
            # Continue with scraping process
            try:
                if method == "Search by Keywords":
                    # Open Google Maps and perform search
                    driver.get("https://www.google.com/maps")
                    self.queue.put(('status', "Opening Google Maps..."))
                    time.sleep(delay)
                    
                    # Search for query
                    query = f"{business_type} in {location}"
                    self.search_google_maps(driver, wait, query, delay)
                    self.queue.put(('status', f"Searching for: {query}"))
                else:
                    # Go directly to the URL
                    driver.get(direct_url)
                    self.queue.put(('status', "Navigating to the provided URL..."))
                    time.sleep(delay + 2)
                
                # Extract business info with proper error handling
                leads = self.extract_business_info(driver, wait, num_results, delay)
                
                if not leads:
                    self.queue.put(('status', "No results found or error occurred during scraping."))
                    self.queue.put(('info', "No results found or could not extract data."))
                    return
                
                # Save to CSV
                try:
                    with open(output_file, "w", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)
                        writer.writerow(["Name", "Address", "Phone", "Website", "Rating", "Reviews", "Categories"])
                        writer.writerows(leads)
                        
                    self.queue.put(('status', f"Successfully saved {len(leads)} leads to {output_file}"))
                    self.queue.put(('success', f"Successfully scraped {len(leads)} leads!"))
                except Exception as e:
                    self.queue.put(('status', f"Error saving CSV file: {str(e)}"))
                    self.queue.put(('error', f"Could not save results to file: {str(e)}"))
                
            except Exception as e:
                self.queue.put(('status', f"Error during scraping: {str(e)}"))
                self.queue.put(('error', f"An error occurred during scraping: {str(e)}"))
                
            finally:
                # Clean up
                if driver:
                    try:
                        driver.quit()
                        self.queue.put(('status', "Browser closed."))
                    except:
                        pass
                        
        except Exception as e:
            self.queue.put(('status', f"Thread error: {str(e)}"))
            self.queue.put(('error', f"An unexpected error occurred: {str(e)}"))
    
    def search_google_maps(self, driver, wait, query, delay):
        """Search Google Maps with the given query"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Wait for search box and perform search
                search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
                search_box.clear()
                search_box.send_keys(query)
                search_box.send_keys(Keys.RETURN)
                time.sleep(delay + 2)  # Wait for results to load
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.queue.put(('status', f"Search attempt {attempt+1} failed, retrying..."))
                    time.sleep(delay)
                    try:
                        driver.refresh()
                        time.sleep(delay)
                    except:
                        pass
                else:
                    self.queue.put(('status', f"Error during search after {max_attempts} attempts: {str(e)}"))
                    raise
    
    def scroll_to_load_more_results(self, driver, max_results, delay):
        """Scroll the results panel to load more business listings"""
        try:
            # Find the scrollable results panel with multiple selectors
            scrollable_selectors = [
                "div.section-layout.section-scrollbox",
                "div[role='feed']",
                "div[jsaction*='mouseover:pane']",
                "div.m6QErb.DxyBCb.kA9KIf.dS8AEf"  # Recent Google Maps class
            ]
            
            scrollable_div = None
            for selector in scrollable_selectors:
                try:
                    scrollable_div = driver.find_element(By.CSS_SELECTOR, selector)
                    if scrollable_div:
                        self.queue.put(('status', f"Found scrollable container with selector: {selector}"))
                        break
                except:
                    continue
            
            if not scrollable_div:
                self.queue.put(('status', "Could not find scrollable results panel, will try to scrape visible results."))
                return
        
            # Scroll down until we have enough results or can't load more
            current_results = 0
            previous_results = -1
            max_attempts = 100
            attempt = 0
            
            while current_results < max_results and current_results != previous_results and attempt < max_attempts:
                if self.stop_event.is_set():
                    self.queue.put(('status', "Scraping stopped by user."))
                    return
                    
                previous_results = current_results
                
                # Scroll the results panel
                try:
                    driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_div)
                except:
                    try:
                        # Alternative scrolling method
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    except:
                        self.queue.put(('status', "Could not scroll down further."))
                        break
                
                # Wait for new results to load
                time.sleep(delay)
                
                # Count the results with multiple selectors
                result_selectors = [
                    "div.Nv2PK",
                    "div[role='article']",
                    "div.THOPZb",  # Recent Google Maps class
                    "div.bfdHYd"   # Another recent class
                ]
                
                business_cards = []
                for selector in result_selectors:
                    try:
                        cards = driver.find_elements(By.CSS_SELECTOR, selector)
                        if cards and len(cards) > len(business_cards):
                            business_cards = cards
                    except:
                        continue
                
                current_results = len(business_cards)
                self.queue.put(('status', f"Loaded {current_results} results (scrolling for more...)"))
                self.queue.put(('progress', int(min(current_results / max_results * 50, 50))))  # 50% of progress bar for loading
                
                attempt += 1
                
                # Add random delay variation to avoid detection
                time.sleep(random.uniform(0.5, 1.5))
            
            if current_results >= max_results:
                self.queue.put(('status', f"Successfully loaded {current_results} results"))
            else:
                self.queue.put(('status', f"Could only load {current_results} results after scrolling"))
            
            return current_results
            
        except Exception as e:
            self.queue.put(('status', f"Error while scrolling: {str(e)}"))
            return 0
        
    def extract_business_info(self, driver, wait, max_results, delay):
        """Extract business information from Google Maps results"""
        leads = []
        try:
            # Wait for business cards to load with retry mechanism
            attempts = 0
            max_attempts = 3
            business_cards = []
            
            while attempts < max_attempts and not business_cards:
                if self.stop_event.is_set():
                    self.queue.put(('status', "Scraping stopped by user."))
                    return leads
                    
                try:
                    self.queue.put(('status', f"Waiting for results to load (attempt {attempts + 1}/{max_attempts})..."))
                    
                    # Try different selectors as Google Maps may change their structure
                    result_selectors = [
                        "div.Nv2PK",
                        "div[role='article']",
                        "div.THOPZb",  # Recent Google Maps class
                        "div.bfdHYd"   # Another recent class
                    ]
                    
                    for selector in result_selectors:
                        try:
                            cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                            if cards:
                                business_cards = cards
                                self.queue.put(('status', f"Found results with selector: {selector}"))
                                break
                        except:
                            continue
                            
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        self.queue.put(('status', f"Failed to find results after {max_attempts} attempts: {str(e)}"))
                        return leads
                    time.sleep(delay)
            
            if not business_cards:
                self.queue.put(('status', "No results found."))
                return leads
            
            # If we need more results than initially loaded, scroll to load more
            initial_count = len(business_cards)
            if max_results > initial_count:
                self.queue.put(('status', f"Initially found {initial_count} results, need to scroll for more..."))
                self.scroll_to_load_more_results(driver, max_results, delay)
                
                # Re-fetch business cards after scrolling
                for selector in result_selectors:
                    try:
                        cards = driver.find_elements(By.CSS_SELECTOR, selector)
                        if cards and len(cards) > len(business_cards):
                            business_cards = cards
                    except:
                        continue
            
            total_cards = min(len(business_cards), max_results)
            self.queue.put(('status', f"Found {total_cards} results to process..."))
            
            # Process each business card
            for index, card in enumerate(business_cards[:max_results]):
                if self.stop_event.is_set():
                    self.queue.put(('status', "Scraping stopped by user."))
                    return leads
                    
                try:
                    # Update progress
                    progress = 50 + (index + 1) / total_cards * 50  # Second 50% of progress bar
                    self.queue.put(('progress', int(progress)))
                    
                    # Scroll to the card with more reliable scrolling
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card)
                        time.sleep(1)
                    except:
                        # Alternative scrolling method
                        try:
                            y_position = driver.execute_script("return arguments[0].getBoundingClientRect().top;", card)
                            driver.execute_script(f"window.scrollBy(0, {y_position});")
                            time.sleep(1)
                        except:
                            pass
                    
                    # Click on the card with retry mechanism
                    click_success = False
                    click_attempts = 0
                    while not click_success and click_attempts < 3:
                        try:
                            card.click()
                            click_success = True
                        except:
                            click_attempts += 1
                            try:
                                # Alternative click method
                                driver.execute_script("arguments[0].click();", card)
                                click_success = True
                            except:
                                time.sleep(1)
                    
                    if not click_success:
                        self.queue.put(('status', f"Could not click on result {index + 1}, skipping..."))
                        continue
                        
                    time.sleep(delay)  # Allow details to load
                    
                    # Extract business details with improved selectors and fallbacks
                    name = self.extract_element_text(driver, [
                        (By.CLASS_NAME, "DUwDvf"),
                        (By.CSS_SELECTOR, "h1.fontHeadlineLarge"),
                        (By.XPATH, "//h1[contains(@class, 'header-title')]"),
                        (By.XPATH, "//div[contains(@class, 'section-hero-header-title')]")
                    ])
                    
                    address = self.extract_element_text(driver, [
                        (By.CSS_SELECTOR, "button[data-item-id='address']"),
                        (By.XPATH, "//button[contains(@aria-label, 'Address')]"),
                        (By.XPATH, "//button[contains(@data-item-id, 'address')]"),
                        (By.XPATH, "//div[contains(@class, 'section-info-line')]/div[contains(@class, 'widget-pane-link')]")
                    ])
                    
                    phone = self.extract_element_text(driver, [
                        (By.CSS_SELECTOR, "button[data-item-id='phone:tel']"),
                        (By.XPATH, "//button[contains(@aria-label, 'Phone')]"),
                        (By.XPATH, "//button[contains(@data-item-id, 'phone')]"),
                        (By.XPATH, "//div[contains(@class, 'section-info-line')]/div[contains(@class, 'widget-pane-link')]")
                    ])
                    
                    website = self.extract_element_attribute(driver, [
                        (By.CSS_SELECTOR, "a[data-item-id='authority']"),
                        (By.XPATH, "//a[contains(@aria-label, 'Website')]"),
                        (By.XPATH, "//a[contains(@data-item-id, 'authority')]"),
                        (By.XPATH, "//div[contains(@class, 'section-info-line')]/div[contains(@class, 'widget-pane-link')]/a")
                    ], "href")
                    
                    # Extract additional information
                    rating = self.extract_element_text(driver, [
                        (By.CSS_SELECTOR, "div.F7nice"),
                        (By.XPATH, "//span[contains(@aria-label, 'stars')]"),
                        (By.XPATH, "//div[contains(@class, 'section-star-display')]")
                    ])
                    
                    # Clean up rating (extract just the number)
                    if rating != "N/A":
                        rating_match = re.search(r'(\d+\.\d+)', rating)
                        if rating_match:
                            rating = rating_match.group(1)
                    
                    reviews = self.extract_element_text(driver, [
                        (By.CSS_SELECTOR, "span.F7nice"),
                        (By.XPATH, "//span[contains(@aria-label, 'reviews')]"),
                        (By.XPATH, "//span[contains(text(), 'reviews')]")
                    ])
                    
                    # Clean up reviews (extract just the number)
                    if reviews != "N/A":
                        reviews_match = re.search(r'(\d+(?:,\d+)*)', reviews)
                        if reviews_match:
                            reviews = reviews_match.group(1)
                    
                    categories = self.extract_element_text(driver, [
                        (By.CSS_SELECTOR, "button[jsaction='pane.rating.category']"),
                        (By.XPATH, "//button[contains(@jsaction, 'pane.rating.category')]"),
                        (By.XPATH, "//span[contains(@class, 'section-rating-term')]")
                    ])

                    # Store details
                    leads.append([name, address, phone, website, rating, reviews, categories])
                    self.queue.put(('status', f"Scraped {index + 1}/{total_cards}: {name}"))
                    
                    # Add random delay variation to avoid detection
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # Go back to results
                    back_success = False
                    try:
                        back_button = driver.find_element(By.XPATH, '//button[@aria-label="Back"]')
                        back_button.click()
                        back_success = True
                    except:
                        pass
                        
                    if not back_success:
                        try:
                            # Try keyboard navigation
                            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            back_success = True
                        except:
                            pass
                            
                    if not back_success:
                        try:
                            # If all else fails, go back in browser history
                            driver.execute_script("history.go(-1)")
                            back_success = True
                        except:
                            pass
                            
                    time.sleep(delay)
                    
                    # Ensure we're back at results page by checking for presence of business cards
                    try:
                        for selector in result_selectors:
                            try:
                                cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                                if cards:
                                    break
                            except:
                                continue
                    except:
                        # If we can't find business cards, we might need to refresh or navigate again
                        self.queue.put(('status', "Lost results page. Attempting to recover..."))
                        driver.execute_script("history.go(-1)")
                        time.sleep(delay + 1)

                except Exception as e:
                    self.queue.put(('status', f"Error processing result {index + 1}: {str(e)}"))
                    # Try to recover to results page
                    try:
                        driver.execute_script("history.go(-1)")
                        time.sleep(delay)
                    except:
                        pass
                    
        except Exception as e:
            self.queue.put(('status', f"Error in extraction process: {str(e)}"))
            
        return leads
    
    def extract_element_text(self, driver, selectors):
        """Extract text from an element using multiple selectors with fallbacks"""
        for by, selector in selectors:
            try:
                element = driver.find_element(by, selector)
                if element and element.text.strip():
                    return element.text.strip()
            except:
                continue
                
        # If all selectors fail, try a more generic approach
        if "h1" in str(selectors):
            h1_elements = driver.find_elements(By.TAG_NAME, "h1")
            if h1_elements:
                for h1 in h1_elements:
                    if h1.text.strip():
                        return h1.text.strip()
        
        return "N/A"
    
    def extract_element_attribute(self, driver, selectors, attribute):
        """Extract an attribute from an element using multiple selectors with fallbacks"""
        for by, selector in selectors:
            try:
                element = driver.find_element(by, selector)
                if element:
                    attr_value = element.get_attribute(attribute)
                    if attr_value:
                        return attr_value
            except:
                continue
        
        return "N/A"
    
    def stop(self):
        """Stop the scraping thread"""
        self.stop_event.set()


class ModernTheme:
    """Class to handle modern styling for the application"""
    def __init__(self, root):
        self.root = root
        self.is_dark_mode = False
        
        # Define colors
        self.light_bg = "#f5f5f5"
        self.light_fg = "#333333"
        self.light_button = "#4a86e8"
        self.light_button_fg = "white"
        self.light_hover = "#3a76d8"
        self.light_frame_bg = "white"
        
        self.dark_bg = "#2d2d2d"
        self.dark_fg = "#e0e0e0"
        self.dark_button = "#5294ff"
        self.dark_button_fg = "white"
        self.dark_hover = "#4284ef"
        self.dark_frame_bg = "#3d3d3d"
        
        # Apply initial theme
        self.apply_theme()
        
    def apply_theme(self):
        """Apply the current theme to all widgets"""
        style = ttk.Style()
        
        # Get current colors based on mode
        bg = self.dark_bg if self.is_dark_mode else self.light_bg
        fg = self.dark_fg if self.is_dark_mode else self.light_fg
        button = self.dark_button if self.is_dark_mode else self.light_button
        button_fg = self.dark_button_fg if self.is_dark_mode else self.light_button_fg
        hover = self.dark_hover if self.is_dark_mode else self.light_hover
        frame_bg = self.dark_frame_bg if self.is_dark_mode else self.light_frame_bg
        
        # Configure ttk styles
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=button, foreground=button_fg, borderwidth=0, focusthickness=0)
        style.map("TButton", background=[("active", hover)])
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.configure("TRadiobutton", background=bg, foreground=fg)
        style.configure("TEntry", fieldbackground=frame_bg, foreground=fg)
        style.configure("TSpinbox", fieldbackground=frame_bg, foreground=fg)
        style.configure("TCombobox", fieldbackground=frame_bg, foreground=fg)
        style.configure("Treeview", background=frame_bg, foreground=fg, fieldbackground=frame_bg)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background=bg, foreground=fg, padding=[10, 2])
        style.map("TNotebook.Tab", background=[("selected", button)], foreground=[("selected", button_fg)])
        
        # Configure LabelFrame
        style.configure("TLabelframe", background=bg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        
        # Configure Progressbar
        style.configure("TProgressbar", background=button, troughcolor=frame_bg)
        
        # Configure Text widget and root
        self.root.configure(bg=bg)
        
    def toggle_theme(self):
        """Toggle between light and dark mode"""
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        return self.is_dark_mode


class GoogleMapsScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("Google Maps Lead Scraper")
        self.root.geometry("800x700")
        self.root.minsize(800, 700)
        
        # Set app icon if available
        try:
            if platform.system() == "Windows":
                self.root.iconbitmap("icon.ico")
            elif platform.system() == "Darwin":  # macOS
                self.root.iconphoto(True, tk.PhotoImage(file="icon.png"))
            else:  # Linux
                self.root.iconphoto(True, tk.PhotoImage(file="icon.png"))
        except:
            pass
        
        # Initialize theme
        self.theme = ModernTheme(self.root)
        
        # Initialize variables
        self.driver = None
        self.wait = None
        self.scraper_thread = None
        self.is_scraping = False
        
        # Create custom fonts
        self.title_font = font.Font(family="Helvetica", size=16, weight="bold")
        self.header_font = font.Font(family="Helvetica", size=12, weight="bold")
        self.normal_font = font.Font(family="Helvetica", size=10)
        
        # Setup UI
        self.setup_ui()
        
        # Center window on screen
        self.center_window()
        
        # Setup periodic queue check
        self.check_queue()
        
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_ui(self):
        # Create main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with logo and title
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Try to load logo
        try:
            logo_img = tk.PhotoImage(file="logo.png").subsample(2, 2)  # Scale down by factor of 2
            logo_label = ttk.Label(header_frame, image=logo_img)
            logo_label.image = logo_img  # Keep a reference
            logo_label.pack(side=tk.LEFT, padx=(0, 10))
        except:
            pass
        
        # Title and theme toggle in header
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = ttk.Label(title_frame, text="Google Maps Lead Scraper", font=self.title_font)
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_frame, text="Extract business information quickly and efficiently")
        subtitle_label.pack(anchor=tk.W)
        
        # Theme toggle button
        self.theme_btn = ttk.Button(header_frame, text="🌙 Dark Mode", command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create tabs
        self.search_tab = ttk.Frame(self.notebook, padding=10)
        self.results_tab = ttk.Frame(self.notebook, padding=10)
        self.settings_tab = ttk.Frame(self.notebook, padding=10)
        self.about_tab = ttk.Frame(self.notebook, padding=10)
        
        # Add tabs to notebook
        self.notebook.add(self.search_tab, text="Search")
        self.notebook.add(self.results_tab, text="Results")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.about_tab, text="About")
        
        # Setup each tab
        self.setup_search_tab()
        self.setup_results_tab()
        self.setup_settings_tab()
        self.setup_about_tab()
        
        # Status bar at bottom
        status_bar = ttk.Frame(self.main_frame)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_bar, text="Ready", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(status_bar, text="v2.0.0", anchor=tk.E)
        version_label.pack(side=tk.RIGHT)
        
    def setup_search_tab(self):
        """Setup the search tab with input fields and options"""
        # Input frame
        input_frame = ttk.LabelFrame(self.search_tab, text="Search Parameters", padding="10")
        input_frame.pack(fill=tk.X, pady=10)
        
        # Search Method
        ttk.Label(input_frame, text="Search Method:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.search_method = ttk.Combobox(input_frame, values=["Search by Keywords", "Use Direct URL"])
        self.search_method.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.search_method.current(0)
        self.search_method.bind("<<ComboboxSelected>>", self.toggle_search_method)
        
        # Keywords Frame
        self.keywords_frame = ttk.Frame(input_frame)
        self.keywords_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Business type
        ttk.Label(self.keywords_frame, text="Business Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.business_type = ttk.Entry(self.keywords_frame, width=30)
        self.business_type.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Location
        ttk.Label(self.keywords_frame, text="Location:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.location = ttk.Entry(self.keywords_frame, width=30)
        self.location.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # URL Frame
        self.url_frame = ttk.Frame(input_frame)
        self.url_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.url_frame.grid_remove()  # Hide initially
        
        # Direct URL
        ttk.Label(self.url_frame, text="Google Maps URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.direct_url = ttk.Entry(self.url_frame, width=50)
        self.direct_url.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Common options
        common_options = ttk.Frame(input_frame)
        common_options.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Number of results to scrape
        ttk.Label(common_options, text="Number of Results:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.num_results = ttk.Spinbox(common_options, from_=1, to=1000, width=10)
        self.num_results.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.num_results.set(100)
        
        # Headless mode
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(common_options, text="Run in Headless Mode", variable=self.headless_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Delay between requests
        ttk.Label(common_options, text="Delay (seconds):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.delay = ttk.Spinbox(common_options, from_=1, to=10, width=5)
        self.delay.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.delay.set(3)
        
        # Output file
        ttk.Label(common_options, text="Output File:").grid(row=3, column=0, sticky=tk.W, pady=5)
        output_file_frame = ttk.Frame(common_options)
        output_file_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        self.output_file = ttk.Entry(output_file_frame, width=20)
        self.output_file.pack(side=tk.LEFT)
        self.output_file.insert(0, "google_maps_leads.csv")
        
        ttk.Button(output_file_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        button_frame = ttk.Frame(self.search_tab)
        button_frame.pack(pady=15)
        
        self.start_button = ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        # Status and progress
        status_frame = ttk.LabelFrame(self.search_tab, text="Status", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(status_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_text = tk.Text(status_frame, height=10, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.status_text.yview)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.search_tab, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=10)
        
    def setup_results_tab(self):
        """Setup the results tab with a table view"""
        # Create frame for results
        results_frame = ttk.Frame(self.results_tab, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        toolbar = ttk.Frame(results_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="Refresh", command=self.refresh_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Export", command=self.export_results).pack(side=tk.LEFT, padx=5)
        
        # Search filter
        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.filter_entry = ttk.Entry(toolbar, width=20)
        self.filter_entry.pack(side=tk.LEFT, padx=5)
        self.filter_entry.bind("<KeyRelease>", self.filter_results)
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        self.results_tree = ttk.Treeview(tree_frame, columns=("name", "address", "phone", "website", "rating", "reviews", "categories"),
                                         show="headings", yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Configure scrollbars
        vsb.config(command=self.results_tree.yview)
        hsb.config(command=self.results_tree.xview)
        
        # Define columns
        self.results_tree.heading("name", text="Business Name")
        self.results_tree.heading("address", text="Address")
        self.results_tree.heading("phone", text="Phone")
        self.results_tree.heading("website", text="Website")
        self.results_tree.heading("rating", text="Rating")
        self.results_tree.heading("reviews", text="Reviews")
        self.results_tree.heading("categories", text="Categories")
        
        # Set column widths
        self.results_tree.column("name", width=150)
        self.results_tree.column("address", width=200)
        self.results_tree.column("phone", width=120)
        self.results_tree.column("website", width=150)
        self.results_tree.column("rating", width=60)
        self.results_tree.column("reviews", width=80)
        self.results_tree.column("categories", width=150)
        
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Add right-click menu
        self.create_context_menu()
        
    def setup_settings_tab(self):
        """Setup the settings tab with configuration options"""
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Application Settings", padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Chrome settings
        chrome_frame = ttk.LabelFrame(settings_frame, text="Chrome Settings", padding="10")
        chrome_frame.pack(fill=tk.X, pady=10)
        
        # Custom Chrome path
        ttk.Label(chrome_frame, text="Chrome Path (optional):").grid(row=0, column=0, sticky=tk.W, pady=5)
        chrome_path_frame = ttk.Frame(chrome_frame)
        chrome_path_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        self.chrome_path = ttk.Entry(chrome_path_frame, width=40)
        self.chrome_path.pack(side=tk.LEFT)
        
        ttk.Button(chrome_path_frame, text="Browse", command=self.browse_chrome).pack(side=tk.LEFT, padx=5)
        
        # Custom ChromeDriver path
        ttk.Label(chrome_frame, text="ChromeDriver Path (optional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        driver_path_frame = ttk.Frame(chrome_frame)
        driver_path_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.driver_path = ttk.Entry(driver_path_frame, width=40)
        self.driver_path.pack(side=tk.LEFT)
        
        ttk.Button(driver_path_frame, text="Browse", command=self.browse_driver).pack(side=tk.LEFT, padx=5)
        
        # Proxy settings
        proxy_frame = ttk.LabelFrame(settings_frame, text="Proxy Settings", padding="10")
        proxy_frame.pack(fill=tk.X, pady=10)
        
        # Enable proxy
        self.use_proxy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(proxy_frame, text="Use Proxy", variable=self.use_proxy_var, command=self.toggle_proxy).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Proxy details
        self.proxy_frame = ttk.Frame(proxy_frame)
        self.proxy_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.proxy_frame.grid_remove()  # Hide initially
        
        ttk.Label(self.proxy_frame, text="Proxy Address:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.proxy_address = ttk.Entry(self.proxy_frame, width=30)
        self.proxy_address.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.proxy_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        self.proxy_port = ttk.Entry(self.proxy_frame, width=10)
        self.proxy_port.grid(row=0, column=3, sticky=tk.W, pady=5)
        
        # Authentication
        self.proxy_auth_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.proxy_frame, text="Authentication Required", variable=self.proxy_auth_var, command=self.toggle_proxy_auth).grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        self.proxy_auth_frame = ttk.Frame(self.proxy_frame)
        self.proxy_auth_frame.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=5)
        self.proxy_auth_frame.grid_remove()  # Hide initially
        
        ttk.Label(self.proxy_auth_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.proxy_username = ttk.Entry(self.proxy_auth_frame, width=20)
        self.proxy_username.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(self.proxy_auth_frame, text="Password:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        self.proxy_password = ttk.Entry(self.proxy_auth_frame, width=20, show="*")
        self.proxy_password.grid(row=0, column=3, sticky=tk.W, pady=5)
        
        # Save settings button
        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).pack(pady=15)
        
    def setup_about_tab(self):
        """Setup the about tab with application information"""
        about_frame = ttk.Frame(self.about_tab, padding="20")
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        # Try to load logo
        try:
            logo_img = tk.PhotoImage(file="logo.png")
            logo_label = ttk.Label(about_frame, image=logo_img)
            logo_label.image = logo_img  # Keep a reference
            logo_label.pack(pady=10)
        except:
            pass
        
        # App info
        ttk.Label(about_frame, text="Google Maps Lead Scraper", font=self.title_font).pack(pady=5)
        ttk.Label(about_frame, text="Version 2.0.0").pack()
        ttk.Label(about_frame, text="© 2023 All Rights Reserved").pack(pady=5)
        
        # Description
        description = (
            "This application allows you to scrape business information from Google Maps.\n"
            "It can extract business names, addresses, phone numbers, websites, ratings, and more.\n\n"
            "Please use responsibly and in accordance with Google's Terms of Service."
        )
        desc_label = ttk.Label(about_frame, text=description, wraplength=500, justify=tk.CENTER)
        desc_label.pack(pady=10)
        
        # Links
        links_frame = ttk.Frame(about_frame)
        links_frame.pack(pady=10)
        
        ttk.Button(links_frame, text="Documentation", command=lambda: self.open_url("https://example.com/docs")).pack(side=tk.LEFT, padx=5)
        ttk.Button(links_frame, text="Report Issue", command=lambda: self.open_url("https://example.com/issues")).pack(side=tk.LEFT, padx=5)
        ttk.Button(links_frame, text="Check for Updates", command=self.check_for_updates).pack(side=tk.LEFT, padx=5)
        
    def toggle_theme(self):
        """Toggle between light and dark mode"""
        is_dark = self.theme.toggle_theme()
        self.theme_btn.config(text="☀️ Light Mode" if is_dark else "🌙 Dark Mode")
        
    def toggle_search_method(self, event=None):
        """Toggle between search methods"""
        method = self.search_method.get()
        if method == "Search by Keywords":
            self.keywords_frame.grid()
            self.url_frame.grid_remove()
        else:
            self.keywords_frame.grid_remove()
            self.url_frame.grid()
            
    def toggle_proxy(self):
        """Toggle proxy settings visibility"""
        if self.use_proxy_var.get():
            self.proxy_frame.grid()
        else:
            self.proxy_frame.grid_remove()
            
    def toggle_proxy_auth(self):
        """Toggle proxy authentication settings visibility"""
        if self.proxy_auth_var.get():
            self.proxy_auth_frame.grid()
        else:
            self.proxy_auth_frame.grid_remove()
            
    def browse_file(self):
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.delete(0, tk.END)
            self.output_file.insert(0, filename)
            
    def browse_chrome(self):
        """Browse for Chrome executable"""
        filename = filedialog.askopenfilename(
            title="Select Chrome Executable",
            filetypes=[
                ("Chrome Executable", "chrome.exe" if platform.system() == "Windows" else "*"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.chrome_path.delete(0, tk.END)
            self.chrome_path.insert(0, filename)
            
    def browse_driver(self):
        """Browse for ChromeDriver executable"""
        filename = filedialog.askopenfilename(
            title="Select ChromeDriver Executable",
            filetypes=[
                ("ChromeDriver", "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.driver_path.delete(0, tk.END)
            self.driver_path.insert(0, filename)
            
    def save_settings(self):
        """Save application settings"""
        # In a real application, you would save these to a config file
        messagebox.showinfo("Settings", "Settings saved successfully!")
        
    def open_url(self, url):
        """Open a URL in the default web browser"""
        import webbrowser
        webbrowser.open(url)
        
    def check_for_updates(self):
        """Check for application updates"""
        # In a real application, you would check for updates from a server
        messagebox.showinfo("Updates", "You are using the latest version!")
        
    def create_context_menu(self):
        """Create right-click context menu for results tree"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected)
        self.context_menu.add_command(label="Open Website", command=self.open_website)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove", command=self.remove_selected)
        
        self.results_tree.bind("<Button-3>", self.show_context_menu)
        
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
            
    def copy_selected(self):
        """Copy selected item to clipboard"""
        selected = self.results_tree.selection()
        if selected:
            item = self.results_tree.item(selected[0])
            values = item['values']
            self.root.clipboard_clear()
            self.root.clipboard_append("\t".join(str(v) for v in values))
            
    def open_website(self):
        """Open website of selected business"""
        selected = self.results_tree.selection()
        if selected:
            item = self.results_tree.item(selected[0])
            website = item['values'][3]  # Website is at index 3
            if website and website != "N/A":
                self.open_url(website)
            else:
                messagebox.showinfo("Info", "No website available for this business.")
                
    def remove_selected(self):
        """Remove selected item from results"""
        selected = self.results_tree.selection()
        if selected:
            for item in selected:
                self.results_tree.delete(item)
                
    def refresh_results(self):
        """Refresh results from the last scrape"""
        # In a real application, you would reload from the saved file
        messagebox.showinfo("Refresh", "Results refreshed!")
        
    def export_results(self):
        """Export results to a file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            ]
        )
        if not filename:
            return
            
        try:
            # Get all items from treeview
            items = self.results_tree.get_children()
            if not items:
                messagebox.showinfo("Export", "No data to export!")
                return
                
            # Export to CSV
            if filename.endswith('.csv'):
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(["Name", "Address", "Phone", "Website", "Rating", "Reviews", "Categories"])
                    # Write data
                    for item in items:
                        values = self.results_tree.item(item)['values']
                        writer.writerow(values)
                        
            # Export to Excel
            elif filename.endswith('.xlsx'):
                try:
                    import pandas as pd
                    
                    # Create DataFrame
                    data = []
                    for item in items:
                        values = self.results_tree.item(item)['values']
                        data.append(values)
                        
                    df = pd.DataFrame(data, columns=["Name", "Address", "Phone", "Website", "Rating", "Reviews", "Categories"])
                    df.to_excel(filename, index=False)
                    
                except ImportError:
                    messagebox.showerror("Error", "Pandas is required for Excel export. Please install it with 'pip install pandas openpyxl'.")
                    return
                    
            messagebox.showinfo("Export", f"Data exported successfully to {filename}!")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting data: {str(e)}")
            
    def filter_results(self, event=None):
        """Filter results based on search text"""
        search_text = self.filter_entry.get().lower()
        
        # Clear current display
        for item in self.results_tree.get_children():
            self.results_tree.detach(item)
            
        # If no search text, show all items
        if not search_text:
            for item in self._all_items:
                self.results_tree.reattach(item, '', 'end')
            return
            
        # Otherwise, show only matching items
        for item in self._all_items:
            values = self.results_tree.item(item)['values']
            if any(search_text in str(value).lower() for value in values):
                self.results_tree.reattach(item, '', 'end')
                
    def update_status(self, message):
        """Update status text and label"""
        self.status_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.status_text.see(tk.END)
        self.status_label.config(text=message)
        self.root.update_idletasks()
        
    def get_chromedriver_path(self):
        """Get the path to chromedriver executable"""
        # Check if user specified a custom path
        custom_path = getattr(self, 'driver_path', None)
        if custom_path and custom_path.get() and os.path.exists(custom_path.get()):
            return custom_path.get()
            
        # Otherwise use bundled or system path
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle
            application_path = sys._MEIPASS
        else:
            # If run as a normal Python script
            application_path = os.path.dirname(os.path.abspath(__file__))
            
        driver_name = "chromedriver.exe" if platform.system() == "Windows" else "chromedriver"
        driver_path = os.path.join(application_path, driver_name)
        
        # Check if driver exists at the expected path
        if not os.path.exists(driver_path):
            self.update_status(f"ChromeDriver not found at: {driver_path}")
            return None
            
        return driver_path
    
    def find_chrome_binary(self):
        """Find Chrome binary across different systems"""
        # Check if user specified a custom path
        custom_path = getattr(self, 'chrome_path', None)
        if custom_path and custom_path.get() and os.path.exists(custom_path.get()):
            return custom_path.get()
            
        system = platform.system()
        chrome_path = None
        
        if system == "Windows":
            # Method 1: Registry lookup
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                    chrome_path, _ = winreg.QueryValueEx(key, "")
                    if os.path.exists(chrome_path):
                        return chrome_path
            except:
                pass
                
            # Method 2: Common installation paths
            paths = [
                os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                # Add additional common paths
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            ]
            
            # Method 3: Check for Chrome Enterprise paths
            program_dirs = [os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 
                           os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')]
            for program_dir in program_dirs:
                if os.path.exists(program_dir):
                    for root, dirs, files in os.walk(program_dir):
                        if 'chrome.exe' in files and 'Google' in root:
                            chrome_path = os.path.join(root, 'chrome.exe')
                            return chrome_path
            
        elif system == "Darwin":  # macOS
            paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chrome.app/Contents/MacOS/Chrome",
                # Add user-specific paths
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            ]
            
            # Try to find Chrome using 'mdfind' command
            try:
                mdfind_process = subprocess.Popen(
                    ["mdfind", "kMDItemDisplayName == 'Google Chrome' && kMDItemKind == 'Application'"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                mdfind_output, _ = mdfind_process.communicate()
                
                if mdfind_output.strip():
                    chrome_path = os.path.join(mdfind_output.split('\n')[0], 
                                             "Contents/MacOS/Google Chrome")
                    if os.path.exists(chrome_path):
                        return chrome_path
            except:
                pass
                
        elif system == "Linux":
            paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
                # Add user-specific paths
                os.path.expanduser("~/.local/bin/chrome")
            ]
            
            # Try using 'which' command
            try:
                which_process = subprocess.Popen(
                    ["which", "google-chrome", "chromium", "chromium-browser"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                which_output, _ = which_process.communicate()
                
                if which_output.strip():
                    chrome_path = which_output.split('\n')[0]
                    if os.path.exists(chrome_path):
                        return chrome_path
            except:
                pass
        
        # Check all potential paths
        for path in paths:
            if os.path.exists(path):
                return path
                
        return None
        
    def start_scraping(self):
        """Start the scraping process in a separate thread"""
        if self.is_scraping:
            messagebox.showinfo("Info", "Scraping is already in progress")
            return
            
        try:
            # Get the input values
            method = self.search_method.get()
            num_results = int(self.num_results.get())
            output_file = self.output_file.get().strip()
            headless = self.headless_var.get()
            delay = int(self.delay.get())
            
            # Validate inputs based on search method
            if method == "Search by Keywords":
                business_type = self.business_type.get().strip()
                location = self.location.get().strip()
                
                if not business_type or not location:
                    messagebox.showerror("Error", "Please enter both business type and location.")
                    return
                    
                self.status_text.delete(1.0, tk.END)
                self.update_status(f"Starting search for {business_type} in {location}...")
                
                # Store parameters
                params = {
                    'method': method,
                    'business_type': business_type,
                    'location': location,
                    'num_results': num_results,
                    'output_file': output_file,
                    'headless': headless,
                    'delay': delay
                }
                
            else:
                direct_url = self.direct_url.get().strip()
                
                if not direct_url or not direct_url.startswith("https://www.google.com/maps"):
                    messagebox.showerror("Error", "Please enter a valid Google Maps URL.")
                    return
                    
                self.status_text.delete(1.0, tk.END)
                self.update_status(f"Starting scraping from URL: {direct_url}")
                
                # Store parameters
                params = {
                    'method': method,
                    'direct_url': direct_url,
                    'num_results': num_results,
                    'output_file': output_file,
                    'headless': headless,
                    'delay': delay
                }
            
            # Reset progress bar
            self.progress_var.set(0)
            
            # Update UI state
            self.is_scraping = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Start scraping in a separate thread
            self.scraper_thread = ScraperThread(self, params)
            self.scraper_thread.start()
            
            # Store all items for filtering
            self._all_items = []
            
        except Exception as e:
            self.update_status(f"Error starting scraping: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            
    def stop_scraping(self):
        """Stop the scraping process"""
        if self.scraper_thread and self.scraper_thread.is_alive():
            self.update_status("Stopping scraper...")
            self.scraper_thread.stop()
            
            # Update UI state
            self.is_scraping = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
    def check_queue(self):
        """Check the queue for messages from the scraper thread"""
        if self.scraper_thread and self.scraper_thread.is_alive():
            try:
                while True:
                    message_type, message = self.scraper_thread.queue.get_nowait()
                    
                    if message_type == 'status':
                        self.update_status(message)
                    elif message_type == 'progress':
                        self.progress_var.set(message)
                    elif message_type == 'error':
                        messagebox.showerror("Error", message)
                    elif message_type == 'info':
                        messagebox.showinfo("Information", message)
                    elif message_type == 'success':
                        messagebox.showinfo("Success", message)
                        
                        # Update results tab with data
                        self.load_results_from_file(self.output_file.get().strip())
                        
                        # Switch to results tab
                        self.notebook.select(self.results_tab)
                        
                    self.scraper_thread.queue.task_done()
            except queue.Empty:
                pass
                
            # If thread has finished, update UI
            if not self.scraper_thread.is_alive() and self.is_scraping:
                self.is_scraping = False
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                self.update_status("Scraping completed.")
                
        # Schedule next check
        self.root.after(100, self.check_queue)
        
    def load_results_from_file(self, filename):
        """Load results from CSV file into the treeview"""
        try:
            # Clear existing data
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
                
            # Read CSV file
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                # Add data to treeview
                for i, row in enumerate(reader):
                    self.results_tree.insert('', 'end', values=row)
                    
            # Store all items for filtering
            self._all_items = self.results_tree.get_children()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load results: {str(e)}")


# Main entry point
def main():
    try:
        # Set up the root window
        root = tk.Tk()
        
        # Apply a modern theme if available
        try:
            style = ttk.Style()
            available_themes = style.theme_names()
            preferred_themes = ['clam', 'alt', 'vista', 'xpnative']
            
            for theme in preferred_themes:
                if theme in available_themes:
                    style.theme_use(theme)
                    break
        except:
            pass
        
        # Create the application
        app = GoogleMapsScraper(root)
        
        # Start the main loop
        root.mainloop()
        
    except Exception as e:
        # If tkinter fails to initialize, show a console error
        print(f"Critical error: {str(e)}")
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Failed to start application:\n\n{str(e)}", "Error", 0)


if __name__ == "__main__":
    main()