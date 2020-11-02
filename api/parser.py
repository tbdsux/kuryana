# MAIN Parser class -> to be used to add new websites
class Parser:
    def __init__(self) -> None:
        self.website = "https://mydramalist.com/"
        self.headers = {
            "Referer": self.website,
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.123 Mobile Safari/537.36",
        }
