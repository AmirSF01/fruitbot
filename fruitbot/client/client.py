from ..network import Network, Socket
from ..utils import Utils
from ..session import Session
from ..models import HeroWithItems
from ..enums import TribeStatuses
from ..data import saveJson
from json import dumps
from typing import List, Union
from threading import Thread


class Client:
    def __init__(self, session_name: str = None, restore_key: str = None, passport: str = None,
                 udid: str = None, base_url: str = None, enc_version=2, time_out: int = None) -> None:
        self.session_name = session_name
        self.socket = Socket()
        self.session = Session(self)
        self.mobile_model = None
        self.queue_number = None
        self.constant_version = "142"

        if self.session.doesSessionExist():
            self.session_data = self.session.loadSessionData()
            self.restore_key, self.passport, self.udid, self.mobile_model = (self.session_data[key] for key in
                                                                             ("restore_key", "passport", "udid",
                                                                              "mobile_model"))
        else:
            self.restore_key = restore_key
            self.passport = passport or Utils.generateRandomPassport()
            self.udid = udid or Utils.generateRandomUdid()
            self.mobile_model = Utils.getRandomMobileModel()
        self.sendRequest = Network(passport=self.passport, enc_version=enc_version, base_url=base_url, time_out=time_out).sendRequest

    def loadPlayer(self, save_session: bool = False, kochava_uid: str = None, appsflyer_uid: str = None,
                   store_type: str = None, metrix_uid: str = None, mobile_model: str = None, device_name: str = None,
                   **params):
        self.mobile_model = mobile_model or self.mobile_model
        params.update({
            "game_version": "1.10.10744",
            "udid": self.udid,
            "os_type": 2,
            "os_version": "9",
            "model": self.mobile_model,
            "device_name": device_name or "unknown",
            "store_type": store_type or "bazar"
        })
        if self.restore_key:
            params["restore_key"] = self.restore_key
        if metrix_uid:
            params["metrix_uid"] = metrix_uid
        if kochava_uid:
            params["kochava_uid"] = kochava_uid
        if appsflyer_uid:
            params["appsflyer_uid"] = appsflyer_uid

        response = self.sendRequest("player/load", params)
        self.restore_key, self.queue_number, self.constant_version = \
            response["restore_key"], response["q"], response["latest_constants_version"]
        self.socket.set_info(user_id=response["id"], tribe_id=(response["tribe"] or {}).get("id"),
                             avatar_id=response["avatar_id"], user_name=response["name"])
        if save_session:
            self.session.saveSession(response)
        return response

    def getConstants(self, mobile_model: str = None, constant_version: Union[str, int] = None,
                     store_type: str = "bazar"):
        response = self.sendRequest("device/constants", {
            "game_version": "1.10.10744",
            "os_version": "9",
            "model": mobile_model or self.mobile_model,
            "constant_version": str(constant_version) or self.constant_version,
            "store_type": store_type
        })
        self.constant_version = response["LATEST_CONSTANTS_VERSION"]
        return response

    def on_message_update(self):
        def handler(func):
            self.socket.add_handler(message_type='chat', func=func)

        return handler

    def on_player_status_update(self):
        def handler(func):
            self.socket.add_handler(message_type='player_status', func=func)
            self.socket.add_handler(message_type='tribe_player_status', func=func)

        return handler

    def on_battle_alert(self):
        def handler(func):
            self.socket.add_handler(message_type='battle_request', func=func)
            self.socket.add_handler(message_type='battle_help', func=func)

        return handler

    def on_battle_update(self):
        def handler(func):
            self.socket.add_handler(message_type='battle_hero_ability', func=func)
            self.socket.add_handler(message_type='battle_update', func=func)
            self.socket.add_handler(message_type='battle_join', func=func)
            self.socket.add_handler(message_type='battle_finished', func=func)

        return handler

    def on_auction_update(self):
        def handler(func):
            self.socket.add_handler(message_type='auction_sold', func=func)
            self.socket.add_handler(message_type='auction_bid', func=func)

        return handler

    def on_tribe_membership_update(self):
        def handler(func):
            self.socket.add_handler(message_type='tribe_join', func=func)
            self.socket.add_handler(message_type='tribe_kick', func=func)

        return handler

    def on_special_event(self, push_message_type: str):
        def handler(func):
            self.socket.add_handler(message_type=push_message_type, func=func)

        return handler

    def stopUpdates(self):
        self.socket.close(reconnect=False)

    def getOpponents(self):
        return self.sendRequest("battle/getopponents")

    def applyInviteCode(self, code: str):
        return self.loadPlayer(invitation_ticket=code)

    def getPlayerInfo(self, player_id: int):
        return self.sendRequest("player/getplayerinfo", {"player_id": player_id})

    def setRecoveryEmail(self, email_address: str):
        return self.sendRequest("player/setemail", {"new_email": email_address})

    def setMobileNumber(self, mobile_number: str):
        return self.sendRequest("player/setmobilenumber", {"mobile_number": mobile_number})

    def setPlayerInfo(self, **params):
        return self.sendRequest("player/setplayerinfo", params)

    def changePlayerName(self, name: str):
        response = self.setPlayerInfo(name=name, lang='fa')
        if response.get('name_changed'):
            self.socket.set_info(user_name=name)
        return response

    def changePlayerAvatar(self, avatar_id: int):
        response = self.setPlayerInfo(avatar_id=avatar_id)
        if response == []:
            self.socket.set_info(avatar_id=avatar_id)
        return response

    def changePlayerMood(self, mood_id: int):
        return self.setPlayerInfo(mood_id=mood_id)

    def changePlayerAddress(self, address: str):
        return self.setPlayerInfo(address=address)

    def changePlayerPhone(self, phone: str):
        return self.setPlayerInfo(phone=phone)

    def changePlayerGender(self, gender: int):
        return self.setPlayerInfo(gender=gender)

    def changePlayerRealName(self, realname: str):
        return self.setPlayerInfo(realname=realname)

    def changePlayerBirthYear(self, birth_year: int):
        return self.setPlayerInfo(birth_year=birth_year)

    def claimAdReward(self):
        return self.sendRequest("player/claimadvertismentreward", {"check": Utils.hashQueueNumber(self.queue_number)})

    def getRecommendedTribes(self):
        return self.sendRequest("tribe/recommended")

    def createTribe(self, name: str, description: str, status: int = TribeStatuses.CLOSED):
        response = self.sendRequest("tribe/create", {
            "name": name,
            "description": description,
            "status": status})
        self.socket.set_info(tribe_id=response["tribe"]["id"])
        return response

    def donateTribe(self, tribe_id: int, gold_amount: int):
        return self.sendRequest("tribe/donate", {
            "tribe_id": tribe_id,
            "gold": gold_amount
        })

    def joinTribe(self, tribe_id: int):
        response = self.sendRequest("tribe/joinrequest", {"tribe_id": tribe_id})
        if response.get('tribe'):
            self.socket.set_info(tribe_id=response['tribe']['id'])
        return response

    def upgradeBank(self):
        return self.sendRequest("tribe/upgrade", {"type": 1007})

    def upgradeGoldMine(self):
        return self.sendRequest("tribe/upgrade", {"type": 1001})

    def upgradeTribeCapability(self, feature: int, tribe_id: int):
        return self.sendRequest("tribe/upgrade", {
            "type": feature,
            "tribe_id": tribe_id
        })

    def cooloffCard(self, card_id: int):
        return self.sendRequest("cards/cooloff", {"card_id": card_id})

    def buyHeroItem(self, item_id: int):
        return self.sendRequest("store/buyheroitem", {"id": item_id})

    def equipHeroesItems(self, heroes_data: List[HeroWithItems], default_base_hero_id: int = None):
        if isinstance(heroes_data, HeroWithItems):
            heroes_data = [heroes_data]
        heroes_info = {
            "hero_details": [
                {
                    "items": [
                        {"position": 1, "base_heroitem_id": item_id} for item_id in hero.left_item_ids
                    ] + [
                        {"position": -1, "base_heroitem_id": item_id} for item_id in hero.right_base_item_ids
                    ],
                    "hero_id": hero.base_hero_id
                } for hero in heroes_data
            ]
        }
        heroes_info["hero_details"] = dumps(heroes_info["hero_details"], separators=(",", ":"))
        if default_base_hero_id:
            heroes_info["default_hero_id"] = default_base_hero_id
        return self.sendRequest("cards/equipheroitems", heroes_info)

    def broadcastMessageToTribe(self, title: str, message: str):
        return self.sendRequest("tribe/broadcast", {
            "title": title,
            "message": message
        })

    def sendMessageToTribe(self, text: str):
        if not self.socket.connected:
            self.comebackToGame(open_socket=True)
        return self.socket.send_tribe_message(text)

    def getTribeBroadcasts(self):
        return self.sendRequest("message/tribebroadcast")

    def editTribeInfo(self, tribe_id: int, status: int, name: str, description: str):
        return self.sendRequest("tribe/edit", {
            "tribe_id": tribe_id,
            "status": status,
            "name": name,
            "description": description
        })

    def invitePlayerToJoinTribe(self, tribe_id: int, player_name: str):
        return self.sendRequest("tribe/invite", {
            "tribe_id": tribe_id,
            "invitee_name": player_name
        })

    def respondToTribeInvite(self, tribe_id: int, request_id: int, accept: bool):
        return self.sendRequest("tribe/decideinvite", {
            "tribe_id": tribe_id,
            "decision": "approve" if accept else "reject",
            "req_id": request_id
        })

    def respondToMembershipRequest(self, tribe_id: int, new_member_id: int, request_id: int, accept: bool):
        return self.sendRequest("tribe/decidejoin", {
            "tribe_id": tribe_id,
            "new_member_id": new_member_id,
            "decision": "approve" if accept else "reject",
            "req_id": request_id
        })

    def promoteTribeMember(self, tribe_id: int, member_id: int):
        return self.sendRequest("tribe/promote", {
            "tribe_id": tribe_id,
            "member_id": member_id
        })

    def searchTribes(self, query: str):
        return self.sendRequest("tribe/find", {"query": query})

    def demoteTribeMember(self, tribe_id: int, member_id: int):
        return self.sendRequest("tribe/demote", {
            "tribe_id": tribe_id,
            "member_id": member_id
        })

    def kickTribeMember(self, tribe_id: int, member_id: int):
        return self.sendRequest("tribe/kick", {
            "tribe_id": tribe_id,
            "member_id": member_id
        })

    def leaveTribe(self):
        response = self.sendRequest("tribe/leave")
        self.socket.unset_info(tribe=True)
        return response

    def getTribeMembers(self, coach_tribe: bool = False):
        return self.sendRequest("tribe/members", {"coach_tribe": coach_tribe})

    def collectMinedGold(self):
        return self.sendRequest("cards/collectgold")

    def getShopItems(self):
        return self.sendRequest("store/getshopitems")

    def searchAuctionCards(self, query_type: int, **params):
        params["query_type"] = query_type
        return self.sendRequest("auction/search", params)

    def searchAuctionCardsByPower(self):
        return self.searchAuctionCards(1)

    def searchAuctionCardsByTime(self):
        return self.searchAuctionCards(3)

    def searchAuctionCardsById(self, base_card_id: int):
        return self.searchAuctionCards(2, base_card_id=base_card_id)

    def searchAuctionCardsByFilters(self, category: int, price_filter: int, card_level: int):
        return self.searchAuctionCards(6, category=category, cheapest=price_filter, rarity=card_level)

    def buyCardPack(self, card_pack_type: int, **params):
        params["type"] = card_pack_type
        return self.sendRequest("store/buycardpack", params)

    def buyHeroCardPack(self, hero_card_pack_type: int):
        return self.buyCardPack(32, base_card_id=hero_card_pack_type)

    def buyBoostPack(self, type: int, with_nectar: bool = True):
        return self.sendRequest("store/buyboostpack", {"with_nectar": with_nectar, "type": type})

    def buyAvatarPack(self):
        return self.sendRequest("store/buyavatarpack")

    def buyPotion(self, amount: int = None):
        return self.sendRequest("player/fillpotion", {"amount": amount} if amount != None else [])

    def potionizeHero(self, amount: int, base_hero_id: int):
        return self.sendRequest("cards/potionize", {
            "potion": amount,
            "hero_id": base_hero_id
        })

    def fullyPotionizeHeroByNectar(self, base_hero_id: int):
        return self.sendRequest("cards/potionize", {"hero_id": base_hero_id})

    def reportMessage(self, message_text: str, player_name: str, message_sent_date: int):
        return self.sendRequest("tribe/reportchat", {
            "message": message_text,
            "player_name": player_name,
            "date": message_sent_date
        })

    def getEventMessages(self):
        return self.sendRequest("message/systemmessages")

    def attackOpponent(self, opponent_id: int, card_ids: list, hero_id: int = None, number_attacks_today: int = 0):
        input = {"opponent_id": opponent_id,
                 "check": Utils.hashQueueNumber(self.queue_number),
                 "attacks_in_today": number_attacks_today}

        if hero_id:
            input["hero_id"] = hero_id
            if hero_id not in card_ids:
                card_ids.append(hero_id)
        input["cards"] = dumps(card_ids, separators=(',', ':'))
        response = self.sendRequest("battle/battle", input)
        if response.get("q"):
            self.queue_number = response.get("q")
        return response

    def doQuest(self, card_ids: list, hero_id: int = None):
        input = {"check": Utils.hashQueueNumber(self.queue_number)}
        if hero_id:
            input["hero_id"] = hero_id
            if hero_id not in card_ids:
                card_ids.append(hero_id)
        input["cards"] = dumps(card_ids, separators=(',', ':'))
        response = self.sendRequest("battle/quest", input)
        return response

    def startLiveBattle(self, opponent_id: int):
        return self.sendRequest("live-battle/livebattle", {"opponent_id": opponent_id})

    def joinLiveBattle(self, main_enemy_id: int, battle_id: int):
        return self.sendRequest("live-battle/livebattlejoin", {
            "mainEnemy": main_enemy_id,
            "battle_id": battle_id
        })

    def ackLiveBattleRequest(self, battle_id: int, already_in_game: bool = False):
        return self.sendRequest("live-battle/livebattleack", {
            "battle_id": battle_id,
            "already_in_game": str(int(already_in_game))
        })

    def respondToAttackRequest(self, accept: bool, battle_id: int):
        return self.sendRequest("live-battle/livebattlechoos", {
            "choice": int(accept),
            "battle_id": battle_id
        })

    def setCardForLiveBattle(self, battle_round: int, card_id: int, battle_id: int):
        return self.sendRequest("live-battle/setcardforlivebattle", {
            "round": battle_round,
            "card": card_id,
            "battle_id": battle_id
        })

    def invokeHeroAbilityInLiveBattle(self, battle_id: int, hero_id: int, ability_type: int):
        return self.sendRequest("live-battle/triggerability", {
            "hero_id": hero_id,
            "ability_type": ability_type,
            "battle_id": battle_id
        })

    def alertTribeToHelpInBattle(self, battle_id: int):
        return self.sendRequest("live-battle/help", {"battle_id": battle_id})

    def withdrawFromBank(self, amount: int):
        return self.sendRequest("player/withdrawfrombank", {"amount": amount})

    def depositToBank(self, amount: int):
        return self.sendRequest("player/deposittobank", {"amount": amount})

    def submitCardForAuction(self, card_id: int):
        return self.sendRequest("auction/setcardforauction", {"card_id": card_id})

    def getMyAuctionBidsHistory(self):
        return self.sendRequest("auction/loadmyparticipatedauctions")

    def getMyAuctionSalesHistory(self):
        return self.sendRequest("auction/loadmyauctions")

    def bidUpCardInAuction(self, auction_id: int):
        return self.sendRequest("auction/bid", {"auction_id": auction_id})

    def sellCardNow(self, auction_id: int):
        return self.sendRequest("auction/sellnow", {"auction_id": auction_id})

    def saveCardInAuctionBidsHistory(self, auction_id: int):
        return self.sendRequest("auction/follow", {"auction_id": auction_id})

    def setOnlineStatus(self, visible: bool = True):
        return self.sendRequest("tribe/invisible", {"status": 1 if visible else 3})

    def pokeTribeMember(self, tribe_id: int, member_id: int):
        return self.sendRequest("tribe/poke", {
            "tribe_id": tribe_id,
            "member_id": member_id
        })

    def openChanceBox(self):
        return self.sendRequest("player/turnthewheel", {
            "store": "4",
            "check": Utils.hashQueueNumber(self.queue_number)
        })

    def assignCardsToBuilding(self, card_ids: list, building_type: int):
        return self.sendRequest("cards/assign", {
            "cards": dumps(card_ids, separators=(",", ":")),
            "type": building_type
        })

    def getMyLeagueRanking(self):
        return self.sendRequest("ranking/league")

    def getTribeRankingBasedOnXP(self):
        return self.sendRequest("ranking/tribe")

    def getTribeRankingBasedOnSeed(self):
        return self.sendRequest("ranking/tribebasedonseed")

    def getGlobalRanking(self):
        return self.sendRequest("ranking/global")

    def getLocalRanking(self):
        return self.sendRequest("ranking/local")

    def getRisingRanking(self):
        return self.sendRequest("ranking/rising")

    def getLeaguesHistory(self, target_weeks: list):
        return self.sendRequest("ranking/leaguehistory", {"rounds": str(target_weeks)})

    def evolveCard(self, sacrifice_card_ids: list):
        return self.sendRequest("cards/evolve", {"sacrifices": str(sacrifice_card_ids)})

    def evolveHeroCard(self, hero_card_id: int):
        return self.evolveCard([hero_card_id])

    def enhanceCard(self, card_id: int, sacrifice_card_ids: list):
        return self.sendRequest("cards/enhance", {
            "card_id": card_id,
            "sacrifices": str(sacrifice_card_ids)
        })

    def redeemGiftCode(self, gift_code: str):
        return self.sendRequest("player/redeemgift", {"code": gift_code})

    def comebackToGame(self, open_socket: bool = False):
        if open_socket:
            if not self.socket.user_id:
                self.loadPlayer()
            self.socket.connect()
            Thread(target=self.socket.receive_messages, args=[]).start()
        return self.sendRequest("player/comeback")

    def scoutBattle(self, do_you_know_this_method_is_useless: bool):
        return self.sendRequest("battle/scout")

    def getMyCollection(self):
        return self.sendRequest("cards/collection")

    def claimFacebookReward(self):
        return self.sendRequest("player/claimfbreward")

    def claimInstagramReward(self):
        return self.sendRequest("player/claiminstagramreward")

    def getAllCardsInfo(self):
        response = self.sendRequest("cards/cardsjsonexport", method="GET")
        saveJson(response, 'cards.json')
        return response

    def getAllFruitsInfo(self):
        response = self.sendRequest("cards/fruitsjsonexport")
        saveJson(response, 'fruits.json')
        return response

    def getCaptcha(self) -> bytes:
        return self.sendRequest("bot/getcaptcha", method="GET")

    def solveCaptcha(self, resp: int):
        return self.sendRequest("bot/challengeresponse", {"resp": resp})

    def getErrorsMessages(self, lang_id: str = "fa-IR"):
        response = self.sendRequest("error/messages", {"lang_id": lang_id})
        return response

    def getConfig(self):
        response = self.sendRequest("config.json", method="GET")
        saveJson(response, 'config.json')
        return response

    def getLanguagepatch(self):
        response = self.sendRequest("player/languagepatch")
        return response
