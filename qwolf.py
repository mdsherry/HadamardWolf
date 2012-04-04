import itertools
import random
import collections
import optparse
import cPickle
State = collections.namedtuple('State', ['villagers','seers','wolves','sorcerers','dead'])

class Game( object ):
	def __init__(self, players, nvillage, nwolf, nseer, nsorc):
		games = []
		if len(players) != nvillage + nwolf + nseer + nsorc:
			raise "Number of players doesn't match number of roles"
		self.players = players
		self.anonplayers = dict( zip( players, random.sample( range(1,len(players)+1), len(players) ) ) )
		p = set( players )
		for villagers in itertools.combinations( p, nvillage ):
			notvillagers = p - frozenset(villagers)
			for seers in itertools.combinations( notvillagers, nseer ):
				evil = notvillagers - frozenset(seers)
				for wolves in itertools.permutations( evil, nwolf ):
					sorcs = evil - frozenset( wolves )
					games.append( State( frozenset(villagers), frozenset(seers), list(wolves), frozenset(sorcs ), set()) )
		self.games = games
		self.nightkills = []
		self.globaldead = []

	def thin( self, proportion=0.25 ):
		"""
		Randomly removes all but the given proportion of game states
		from consideration, in order to make a more comprehensible game.
		"""
		self.games = random.sample( self.games, proportion * len( self.games ) )

	def safeseer( self, player ):
		"""
		Picks a random game in which the player is a seer, then picks out 
		another player who is on Team Good in that game. It then removes
		all games in which the player is seer and the other player is not 
		on Team Good.
		The identity of this other player is returned. The other player will 
		never be the player passed in.
		"""
		player_is_seer = [ x for x in self.games if player in x.seers] 
		game = random.choice( player_is_seer )
		target = player
		while target == player:
			target = random.choice(tuple(game.villagers | game.seers))
		self.games = [ x for x in self.games if target in x.villagers or target in x.seers or player not in x.seers ]
		return target

	def seer( self, player, target ):
		"""
		Picks a random game in which the player is a seer, and determines 
		whether the target is good or evil in that game. All games in which
		the player is seer, and the target's alignment doesn't match the
		vision are removed.
		"""
		player_is_seer = [ x for x in self.games if player in x.seers ]
		outcome = random.choice( player_is_seer )
		if target in outcome.villagers or target in outcome.seers:
			self.games = [x for x in self.games if target in x.villagers or target in x.seers or player not in x.seers ]
			return True
		else:
			self.games = [x for x in self.games if target in x.wolves or target in x.sorcerers or player not in x.seers ]
			return False

	def safesorc( self, player ):
		"""
		Picks a random game in which the player is a sorcerer, then picks out 
		another player who is not a seer. All games in which the player is
		sorcerer and the other player is seer are removed.
		The identity of this other player is returned. The other player will 
		never be the player passed in.
		"""
		player_is_sorc = [ x for x in self.games if player in x.seers ]
		game = random.choice( player_is_sorc )
		target = random.choice(tuple(game.villagers | game.seers))
		self.games = [ x for x in self.games if target in x.villagers or target in x.seers or player not in x.seers ]
		return target

	def sorc( self, player, target ):
		"""
		Picks a random game in which the player is a sorcerer, and determines 
		whether the target is a seer in that game. All games in which
		the player is sorcerer, and the target's seer status doesn't match the
		vision are removed.
		"""
		player_is_sorc = [ x for x in self.games if player in x.sorcerers ]
		outcome = random.choice( player_is_sorc )
		if target in outcome.seers:
			self.games = [x for x in self.games if target in x.seers or player not in x.sorcerers ]
			return True
		else:
			self.games = [x for x in self.games if target not in x.seers or player not in x.sorcerers ]
			return False

	def lynch( self, target, lynch=True ):
		"""
		Kill a player, resolving their true state. Pass in 'False' for the 
		'lynch' parameter if the player didn't die from lynching. This will
		prevent it from prefiltering out all games in which the player died
		before this point.
		After this, it checks to see if anyone else has died from the state 
		collapse.
		"""
		if lynch:
			self.games = [x for x in self.games if target not in x.dead]
		outcome = random.choice( self.games )
		if target in outcome.villagers:
			print target, "was a villager!"
			self.games = [x for x in self.games if target in x.villagers]
		elif target in outcome.seers:
			print target, "was a seer!"
			self.games = [x for x in self.games if target in x.seers]
		elif target in outcome.wolves:
			print target, "was a werewolf!"
			self.games = [x for x in self.games if target in x.wolves]
			for game in self.games:
				if game.wolves[0] == target:
					game.wolves[:] = game.wolves[1:] + game.wolves[:1]
		elif target in outcome.sorcerers:
			print target, "was a sorceror!"
			self.games = [x for x in self.games if target in x.sorcerers]
		for game in self.games:
			game.dead.add( target )
		if target not in self.globaldead:
			self.globaldead.append( target )
			self.find_new_dead()

	def find_new_dead( self ):
		"""
		Find all players who are dead in all games, but weren't known
		to be dead before this point. The newly dead players have their
		roles resolved.
		"""
		for player in self.players:
			alive = False
			if player in self.globaldead:
				continue
			for game in self.games:
				if player not in game.dead:
					alive = True
					break
			if not alive:
				print player, "is surprised to find themselves actually dead."
				self.globaldead.append( player )
				self.lynch( player, False )

	def kill( self, player, target ):
		"""
		Add the target to the dead list in all games in which 
		the player is the dominant wolf.
		"""
		self.games = [x for x in self.games if (player != x.wolves[0]) or (target not in x.wolves)]
		for game in self.games:
			if player == game.wolves[0]:
				game.dead.add( target )


	def probs( self ):
		"""
		Generate the role probability table.
		"""
		odds = dict( [( player, [0]*5) for player in self.players ] )
		ngames = float(len(self.games))
		for game in self.games:
			for player in game.villagers:
				odds[player][0] += 1
			for player in game.seers:
				odds[player][1] += 1
			for player in game.wolves:
				odds[player][2] += 1
			for player in game.sorcerers:
				odds[player][3] += 1
			for player in game.dead:
				odds[player][4] += 1
		print
		print "{0:^12}{1:^11}{2:^11}{3:^11}{4:^11}{5:^11}".format( "Player", "Villager", "Seer", "Wolf", "Sorcerer", "Dead" )
		print "{0:^12}{1:^11}{2:^11}{3:^11}{4:^11}{5:^11}".format( "========", "========", "========", "========", "========", "========" )
		for player in self.players:
			print "{0:<10}{1:>10.2f}%{2:>10.2f}%{3:>10.2f}%{4:>10.2f}%{5:>10.2f}%".format( player, 
				odds[player][0] * 100 / ngames,
				odds[player][1] * 100 / ngames,
				odds[player][2] * 100 / ngames, 
				odds[player][3] * 100 / ngames, 
				odds[player][4] * 100 / ngames )
		print
		return odds

	def get_active_wolves( self ):
		"""
		Returns the set of players who are the dominant wolf in 
		at least one game.
		"""
		active = set()
		for game in self.games:
			if game.wolves[0] in game.dead:
				print "Oh dear. Handling succession."
				game.wolves[:] = game.wolves[1:] + game.wolves[:1]
			active.add( game.wolves[0] )
		return active

	def werewolf_sets( self ):
		"""
		Returns the set of (living) wolf packs that exist in at least one game.
		"""
		wolves = set()
		for game in self.games:
			wolves.add( frozenset( game.wolves ) - game.dead )
		return wolves

if __name__ == "__main__":
	g = Game( ("Alice", "Bob", 'Carol', "Dave", "Eve", "Frank", "Gerald","Howie","Ivan","Jan","Kyle") , 6,3,1,1 )
	print len(g.games)

	for player in g.players:
		print player, "-->", g.safeseer( player )

	print len(g.games)
	l = list(g.get_active_wolves())
	for player, p2 in zip(l, l[1:] + l[:1]):
		g.kill( player, p2 )
	print len(g.games)
	g.kill( "Alice", "Carol" )
	g.lynch( "Carol" )
	g.kill( "Howie", "Ivan" )
	print len(g.games)
	g.probs()
	print g.werewolf_sets()
