from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("user-data-dir=C:/Users/Dejan/AppData/Local/Google/Chrome/User Data")
chrome_options.add_argument("profile-directory=Default")

# Specify the path to ChromeDriver
chrome_driver_path = 'C:/WebDrivers/chrome-win64/chrome.exe'

# Create a Service object with the path to the driver
service = Service(executable_path=chrome_driver_path)
print("Service created")
# Initialize WebDriver with the Service object and Chrome options
driver = webdriver.Chrome(service=service, options=chrome_options)
print("Driver initialized")
# Open the authenticated page
driver.get('https://portal.clarin.ivdnt.org/corpus-frontend-chn/chn-extern/search/hits?filter=languageVariant%3A%28"NN"%29+AND+%28witnessYear_from%3A%5B2000+TO+2024%5D+OR+witnessYear_to%3A%5B2000+TO+2024%5D%29&first=0&group=hit%3Alemma%3Ai&number=20&patt=%5B%5D&interface=%7B"form"%3A"explore"%2C"exploreMode"%3A"frequency"%7D')
print("got em")
# Now you can scrape or interact with the page
