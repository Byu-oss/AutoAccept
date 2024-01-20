import requests
import time
import json
import configparser

class Login:
    config = configparser.ConfigParser()
    config.read('login.ini')
    username = config['DEFAULT']['Username']
    password = config['DEFAULT']['Password']

class Application:
    class Config:
        class Sleeps:
            Animation = 0.2
            Check = 2.5
            Accept = 3

        class Configuration:
            MinFollowers = 600
            MutualFollowers = False
            MinMutualFollowers = 3

        class URLS:
            Cookies = "https://www.instagram.com/accounts/login/"
            Login = "https://www.instagram.com/accounts/login/ajax/"
            Requests = "https://www.instagram.com/accounts/activity/?__a=1&include_reel=true"
            AccountDetails = "https://www.instagram.com/%s/?__a=1"
            SetPrivacy = "https://www.instagram.com/accounts/set_private/"
            AcceptRequest = "https://www.instagram.com/web/friendships/%s/approve/"
            IgnoreRequest = "https://www.instagram.com/web/friendships/%s/ignore/"
            TwoStep = "https://www.instagram.com/accounts/login/two_factor?__a=1"
            TwoStepConfirm = "https://www.instagram.com/accounts/login/ajax/two_factor/"

        class Misc: 
            FailedAccept = False
            AnimationChecks: int
            FailReason: str
            TwoStepID: str

        class Account:
            username: str
            id: int
            follower_count: int
            mutual_followers: int

            def __init__(self, username, id, follower_count, mutual_followers):
                self.username = username
                self.id = id
                self.follower_count = follower_count
                self.mutual_followers = mutual_followers

    def __init__(self, user: str, passw: str):
        self.s = requests.session()
        self.username = user
        self.password = passw
        self.s.headers.update({
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com/accounts/login/',
            'user-agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.2; zh) AppleWebKit/522.13.1 (KHTML, like Gecko) Version/3.0.2 Safari/522.13.1',
            'x-instagram-ajax': '1',
            'x-requested-with': 'XMLHttpRequest'
        })

    def start_process(self):
        self.login_process()

    def update_token(self, data: str) -> dict or None:
        self.s.headers.update({"x-csrftoken": data.cookies.get_dict()['csrftoken']})
        return data

    def get_request(self, url: str, data: str) -> dict or None:
        return self.update_token(self.s.get(url, data=data))

    def post_request(self, url: str, data: str) -> dict or None:
        return self.update_token(self.s.post(url, data=data))

    def login_process(self):
        self.get_request(self.Config.URLS.Cookies, "{}")
        login_data = {
            'username': self.username,
            'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{self.password}",
            'queryParams': '{}',
            'optIntoOneTap': 'true'
        }
        login_request = self.post_request(self.Config.URLS.Login, data=login_data)

        if login_request.status_code == 400:
            if login_request.json()['two_factor_required']:
                ''' set 2fa token, call 2fa function '''
                self.Config.Misc.TwoStepID = login_request.json()['two_factor_info']['two_factor_identifier']
                self.two_factor_auth()
            else: raise Exception(f"[!] {self.username} failed to login | {login_request.status_code}")
        else:
            if login_request.json()['authenticated']:
                print(f"\n[+] {self.username} logged in | {login_request.status_code}")
                self.privacy_settings()
            else: raise Exception(f"[!] {self.username} failed to login | {login_request.status_code}")

    def two_factor_auth(self):
        self.s.headers.update({"referer": self.Config.URLS.TwoStep})
        two_factor_data = {
            'username': self.username,
            'verificationCode': int(input(f"[?] {self.username} | Two Step Code: ")),
            'identifier': self.Config.Misc.TwoStepID,
            'queryParams': "{}"
        }
        two_factor_request = self.post_request(self.Config.URLS.TwoStepConfirm, data=two_factor_data)
        if two_factor_request.status_code == 200: self.privacy_settings()
        else: raise Exception(f"[!] Unable to verify Two Step | {self.username} | {two_factor_request.text}")

    def privacy_settings(self):
        CheckPrivate = self.s.get(self.Config.URLS.AccountDetails % (self.username))
        if not CheckPrivate.json()['graphql']['user']['is_private']:
            print(f"[~] {self.username} is not private, changing settings.")
            SetPrivate = self.post_request(self.Config.URLS.SetPrivacy, data={'is_private': 'true'})
            if SetPrivate.status_code == 200: 
                print(f"[~] {self.username} changed to private, continuing")
                self.accept_requests()
            else: raise Exception(f"[~] {self.username} unable to change, continuting")
        else: self.accept_requests()

    def accept_requests(self):
        time.sleep(self.Config.Sleeps.Check)
        print(f"[!] {self.username} logged in, privated, monitoring")
        while True:
            try:
                time.sleep(self.Config.Sleeps.Check)
                account_info_request = self.s.get(self.Config.URLS.Requests).json()['graphql']['user']['edge_follow_requests']['edges']
                if len(account_info_request) > 0:
                    print(f"[+] Follow request from @{account_info_request[0]['node']['username']} | {self.username}")
                    account_details_request = self.get_request(self.Config.URLS.AccountDetails % (account_info_request[0]['node']['username']), "{}").json()['graphql']['user']
                    account_info = self.Config.Account(account_info_request[0]['node']['username'],account_info_request[0]['node']['id'],account_details_request['edge_followed_by']['count'],account_details_request['edge_mutual_followed_by']['count'])
                    if account_info.follower_count < self.Config.Configuration.MinFollowers:
                        self.Config.Misc.FailedAccept = True
                        self.Config.Misc.FailReason = f"{account_info.follower_count}/{self.Config.Configuration.MinFollowers} followers"

                    if self.Config.Configuration.MutualFollowers:
                        if account_info.mutual_followers < self.Config.Configuration.MinMutualFollowers:
                            self.Config.Misc.FailedAccept = True
                            self.Config.Misc.FailReason = f" {account_info.mutual_followers}/{self.Config.Configuration.MinMutualFollowers} mutual followers"
                    if self.Config.Misc.FailedAccept:
                        print(f"[-] Rejected @{account_info_request[0]['node']['username']} | {self.Config.Misc.FailReason} | {self.username}")
                        self.post_request(self.Config.URLS.IgnoreRequest % (account_info_request[0]['node']['id']))
                    else:
                        time.sleep(self.Config.Sleeps.Accept)
                        AcceptRequest = self.post_request(self.Config.URLS.AcceptRequest % (account_info_request[0]['node']['id']))
                        if AcceptRequest.status_code == 200: print(f"[+] Accepted @{account_info_request[0]['node']['username']} | {self.username}")
            except Exception as e: raise Exception(e)

App = Application(Login.username, Login.password)
App.start_process()