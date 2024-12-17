import subprocess
import time

# Function to read domains from the input file
def read_domains(file_path):
    try:
        with open(file_path, "r") as file:
            domains = [line.strip() for line in file if line.strip() and not line.startswith("#")]
        return domains
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found!")
        exit(1)

# Function to prompt user for confirmation
def ask_confirmation(batch_size):
    while True:
        choice = input(f"Press Enter to open the next batch of {batch_size} links, or type 'q' to quit: ")
        if choice.lower() == "q":
            print("Exiting. No more links will be opened.")
            exit(0)
        elif choice == "":
            return
        else:
            print("Invalid input. Press Enter to continue or 'q' to quit.")

# Function to open links using Brave browser
def open_with_brave(url):
    brave_command = ["brave", url]  # Replace "brave" with the full path to Brave if necessary
    try:
        subprocess.Popen(brave_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: Brave browser is not installed or not found in PATH.")
        exit(1)

# Main function
def open_domains(file_path, batch_size=20, delay=1):
    domains = read_domains(file_path)
    total_links = len(domains)
    print(f"Total domains to open: {total_links}")

    counter = 0
    for domain in domains:
        # Add "http://" if missing
        if not domain.startswith(("http://", "https://")):
            domain = "http://" + domain

        # Open the link in Brave browser
        print(f"Opening link {counter + 1}: {domain}")
        open_with_brave(domain)
        counter += 1

        # Delay to avoid overwhelming the system
        time.sleep(delay)

        # Prompt user every 'batch_size' links
        if counter % batch_size == 0:
            print(f"Opened {counter} links so far.")
            ask_confirmation(batch_size)

    print("All domains have been opened.")

# Entry point
if __name__ == "__main__":
    import sys

    # Check if the file path is provided
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file_with_domains>")
        exit(1)

    file_path = sys.argv[1]
    open_domains(file_path)
