
# (File) bot.py
# (Version) 5.0
# (Comments) Super old Instagram project I was working on
#         -> Logs into Instagram account (2step allowed)
#         -> Sets Instagram to private
#         -> Accept follow requests quickly

import requests, time, sys, threading, getpass, os, json

if len(sys.argv) < 2: sys.exit(f"Usage: {sys.argv[0]} <account file>")

class AutoAccept:
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
            Requests = "https://i.instagram.com/api/v1/friendships/pending/"
            AccountDetails = "https://i.instagram.com/api/v1/users/web_profile_info/?username=%s"
            SetPrivacy = "https://www.instagram.com/accounts/set_private/"
            AcceptRequest = "https://www.instagram.com/web/friendships/%s/approve/"
            IgnoreRequest = "https://www.instagram.com/web/friendships/%s/ignore/"
            TwoStep = "https://www.instagram.com/accounts/login/two_factor?__a=1"
            TwoStepConfirm = "https://www.instagram.com/accounts/login/ajax/two_factor/"

        class Misc: 
            FailedAccept = False
            FailReason = ""
            AnimationChecks = 0
            TwoStepID = ""

    def __init__(self, user, passw):
        self.s = requests.session()
        self.username = user
        self.password = passw
        self.s.headers.update({
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com',
            'user-agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.2; zh) AppleWebKit/522.13.1 (KHTML, like Gecko) Version/3.0.2 Safari/522.13.1'
        })

    def Login(self):
        LoginData = {
            'username': self.username,
            'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{self.password}",
            'queryParams': '{}',
            'optIntoOneTap': 'true'
        }
        Grab = self.s.get(self.Config.URLS.Cookies)
        self.s.headers.update({"x-csrftoken": Grab.cookies.get_dict()['csrftoken']})
        AccLogin = self.s.post(self.Config.URLS.Login, data=LoginData)
        if AccLogin.status_code == 400:
            if AccLogin.json()['two_factor_required']:
                self.Config.Misc.TwoStepID = AccLogin.json()['two_factor_info']['two_factor_identifier']
                self.TwoStep()
        else:
            if AccLogin.json()['authenticated']:
                print(f"\n[+] {self.username} logged in | {AccLogin.status_code}")
                self.s.headers.update({"x-csrftoken": AccLogin.cookies.get_dict()['csrftoken']})
                self.PrivateSet()
            else: print(f"[!] {self.username} failed to login | {AccLogin.status_code}")

    def TwoStep(self):
        self.s.headers.update({"referer": "https://www.instagram.com/accounts/login/two_factor?next=%2F"})
        Data = {
            'username': self.username,
            'verificationCode': int(input(f"[?] {self.username} | Two Step Code: ")),
            'identifier': self.Config.Misc.TwoStepID,
            'queryParams': "{}"
        }
        _ = self.s.post(self.Config.URLS.TwoStepConfirm, data=Data)
        if _.status_code == 200:
            self.s.headers.update({"x-csrftoken": _.cookies.get_dict()['csrftoken']})
            self.Accept()
        else: print(f"[!] Unable to verify Two Step | {self.username} | {_.text}")

    def Animation(self):
        while self.Config.Misc.AnimationChecks <= 100:
            StartAni = "*" * int(self.Config.Misc.AnimationChecks / 5)
            print(f"\rInitilizing AutoAccepter [{StartAni}] ({self.Config.Misc.AnimationChecks}/100%)", end="")
            time.sleep(self.Config.Sleeps.Animation)
            self.Config.Misc.AnimationChecks += 5
        self.Login()

    def PrivateSet(self):
        CheckPrivate = self.s.get(self.Config.URLS.AccountDetails % (self.username))
        if not CheckPrivate.json()['graphql']['user']['is_private']:
            print(f"[~] {self.username} is not private, changing settings.")
            SetPrivate = self.s.post(self.Config.URLS.SetPrivacy, data={'is_private': 'true'})
            if SetPrivate.status_code == 200: 
                print(f"[~] {self.username} changed to private, continuing")
                self.Accept()
            else: 
                print(f"[~] {self.username} unable to change, continuting")
                return
        else: self.Accept()

    def Accept(self):
        while True:
            try:
                self.Config.Misc.FailedAccept = False
                self.Config.Misc.FailReason = ""
                time.sleep(self.Config.Sleeps.Check)
                followRequests = self.s.get(self.Config.URLS.Requests)
                print(followRequests)
                followRequests = followRequests.json()['users'][0]
                if len(followRequests) > 0:
                    print(f"[+] Follow request from @{followRequests['username']} | {self.username}")
                    accountInfo = self.s.get(self.Config.URLS.AccountDetails % (followRequests['username'])).json()['data']['user']
                    
                    if accountInfo['edge_followed_by']['count'] < self.Config.Configuration.MinFollowers:
                        self.Config.Misc.FailedAccept = True
                        self.Config.Misc.FailReason += f"{accountInfo['edge_followed_by']['count']}/{self.Config.Configuration.MinFollowers} followers"
                        
                    if self.Config.Configuration.MutualFollowers:
                        if accountInfo['edge_mutual_followed_by']['count'] < self.Config.Configuration.MinMutualFollowers:
                            self.Config.Misc.FailedAccept = True
                            self.Config.Misc.FailReason += f" {accountInfo['edge_mutual_followed_by']['count']}/{self.Config.Configuration.MinMutualFollowers} mutual followers"
                            
                    if self.Config.Misc.FailedAccept:
                        print(f"[-] Rejected @{followRequests[0]['node']['username']} | {self.Config.Misc.FailReason} | {self.username}")
                        self.s.post(self.Config.URLS.IgnoreRequest % (followRequests[0]['node']['id']))
                        
                    else:
                        time.sleep(self.Config.Sleeps.Accept)
                        AcceptRequest = self.s.post(self.Config.URLS.AcceptRequest % (followRequests[0]['node']['id']))
                        if AcceptRequest.status_code == 200: print(f"[+] Accepted @{followRequests[0]['node']['username']} | {self.username}")
            except Exception as e: print(e)

# Multiple Accounts
#with open(sys.argv[1], 'r') as _logs:
#    for _acc in _logs:
#        _newLog = _acc.split(":")
#        Accepting = AutoAccept(_newLog[0], _newLog[1])
#        if len(_logs.read().split("\n")) == 0: threading.Thread(target=Accepting.Animation).start()
#        else: threading.Thread(target=Accepting.Login).start()


# Single login with account file
with open(sys.argv[1], 'r') as _logs:
    for _acc in _logs:
        _newLog = _acc.split(":")
        Accepting = AutoAccept(_newLog[0], _newLog[1])
        threading.Thread(target=Accepting.Login).start()
