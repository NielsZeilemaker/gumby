#!/usr/bin/env python
# social_client.py ---
#
# Filename: social_client.py
# Description:
# Author: Niels Zeilemaker
# Maintainer:
# Created: Mon Oct 28 14:10:00 2013 (+0200)

# Commentary:
#
#
#
#

# Change Log:
#
#
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
#
#

# Code:
import sys
from os import path
from random import sample
from sys import path as pythonpath
from hashlib import sha1

from gumby.experiments.dispersyclient import DispersyExperimentScriptClient, call_on_dispersy_thread, main

from twisted.python.log import msg

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

class SocialClient(DispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        from Tribler.community.privatesocial.community import PoliSocialCommunity
        DispersyExperimentScriptClient.__init__(self, *argv, **kwargs)
        self.community_class = PoliSocialCommunity

        self.friends = set()
        self.not_connected_friends = set()
        self.foafs = set()
        self.not_connected_foafs = set()

        self.peercache = False

        self.set_community_kwarg('integrate_with_tribler', False)
        self.set_community_kwarg('encryption', False)
        self.set_community_kwarg('max_prefs', 100)
        self.set_community_kwarg('max_fprefs', 100)
        self.set_community_kwarg('use_cardinality', False)

    def start_dispersy(self):
        DispersyExperimentScriptClient.start_dispersy(self)

        # as i'm cpu bound, lowering the number of bits of the elliptic curve
        self._my_member = self._dispersy.callback.call(self._dispersy.get_new_member, (u"NID_secp112r1",))

        self.community_args = (self._my_member,)

    def registerCallbacks(self):
        self.scenario_runner.register(self.my_key, 'my_key')
        self.scenario_runner.register(self.add_friend, 'add_friend')
        self.scenario_runner.register(self.add_foaf, 'add_foaf')
        self.scenario_runner.register(self.connect_to_friends, 'connect_to_friends')
        self.scenario_runner.register(self.set_community_class, 'set_community_class')

    def peertype(self, peertype):
        DispersyExperimentScriptClient.peertype(self, peertype)
        if peertype == "peercache":
            self.peercache = True

    def set_community_class(self, commtype):
        from Tribler.community.privatesocial.community import NoFSocialCommunity, PSocialCommunity, HSocialCommunity, PoliSocialCommunity
        if commtype == "nof":
            self.community_class = NoFSocialCommunity
        elif commtype == "p":
            self.community_class = PSocialCommunity
        elif commtype == "h":
            self.community_class = HSocialCommunity
        elif commtype == "poli":
            self.community_class = PoliSocialCommunity
        else:
            raise RuntimeError("undefined class type, %s" % commtype)

    @call_on_dispersy_thread
    def online(self):
        DispersyExperimentScriptClient.online(self)

        self._manual_create_introduction_request = self._community.create_introduction_request
        self._community.create_introduction_request = lambda destination, allow_sync: self._manual_create_introduction_request(destination, False)

    @call_on_dispersy_thread
    def my_key(self, key):
        from Tribler.community.privatesemantic.rsa import bytes_to_key

        keyhash = long(sha1(str(key)).hexdigest(), 16)
        self._community._mypref_db.addMyPreference(keyhash, {})

        key = key.replace("_", " ")
        key = bytes_to_key(key)
        self._community._friend_db.add_my_key(key, keyhash)

    @call_on_dispersy_thread
    def add_friend(self, peer_id, key):
        from Tribler.community.privatesemantic.rsa import bytes_to_key

        peer_id = int(peer_id)
        ipport = self.get_peer_ip_port(peer_id)

        # if we don't get the ipport, then this peer isn't deployed to the das
        if ipport:
            keyhash = long(sha1(str(key)).hexdigest(), 16)
            self._community._mypref_db.addMyPreference(keyhash, {})

            key = key.replace("_", " ")
            key = bytes_to_key(key)
            self._community._friend_db.add_friend(str(peer_id), key, keyhash)

            self.friends.add(ipport)
            self.not_connected_friends.add(ipport)

            self._dispersy.callback.persistent_register(u"monitor_friends", self.monitor_friends)

    @call_on_dispersy_thread
    def add_foaf(self, peer_id):
        peer_id = int(peer_id)
        ipport = self.get_peer_ip_port(peer_id)

        if ipport:
            self.foafs.add(ipport)
            self.not_connected_foafs.add(ipport)

            self._dispersy.callback.persistent_register(u"monitor_friends", self.monitor_friends)

    @call_on_dispersy_thread
    def connect_to_friends(self):
        friendsaddresses = self.friends
        foafsaddresses = self.foafs
        if self.peercache:
            friendsaddresses = sample(friendsaddresses, int(len(friendsaddresses) * 0.36))
            foafsaddresses = sample(foafsaddresses, int(len(foafsaddresses) * 0.36))

        for ipport in friendsaddresses:
            self._community._peercache.add_peer([keyhash for _, keyhash in self._community._friend_db.get_my_keys()], *ipport)

        for ipport in foafsaddresses:
            self._community._peercache.add_peer([], *ipport)

        # use peercache to connect to friends
        self._community.connect_to_peercache(sys.maxint)

        # enable normal discovery of foafs
        self._community.create_introduction_request = self._manual_create_introduction_request

    def monitor_friends(self):
        prev_scenario_statistics = {}
        prev_scenario_debug = {}

        while True:
            for sock_addr in self.friends:
                if self._community.is_taste_buddy_sock(sock_addr):
                    if sock_addr in self.not_connected_friends:
                        self.not_connected_friends.remove(sock_addr)
                else:
                    self.not_connected_friends.add(sock_addr)

            for sock_addr in self.foafs:
                if self._community.is_taste_buddy_sock(sock_addr):
                    if sock_addr in self.not_connected_foafs:
                        self.not_connected_foafs.remove(sock_addr)
                else:
                    self.not_connected_foafs.add(sock_addr)

            if self.friends:
                connected_friends = len(self.friends) - len(self.not_connected_friends)
                bootstrapped = connected_friends / float(len(self.friends))
            else:
                bootstrapped = 0

            if self.foafs:
                connected_foafs = len(self.foafs) - len(self.not_connected_foafs)
                bootstrapped_foafs = connected_foafs / float(len(self.foafs))
            else:
                bootstrapped_foafs = 0

            prev_scenario_statistics = self.print_on_change("scenario-statistics", prev_scenario_statistics, {'bootstrapped': bootstrapped, 'bootstrapped_foafs': bootstrapped_foafs})
            prev_scenario_debug = self.print_on_change("scenario-debug", prev_scenario_debug, {'not_connected':list(self.not_connected_friends), 'create_time_encryption':self._community.create_time_encryption, 'create_time_decryption':self._community.create_time_decryption, 'receive_time_encryption':self._community.receive_time_encryption})
            yield 5.0

if __name__ == '__main__':
    SocialClient.scenario_file = "social.scenario"
    main(SocialClient)

#
# social_client.py ends here
