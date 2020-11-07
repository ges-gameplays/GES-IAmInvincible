from GamePlay import GEScenario
from .Utils import GetPlayers
from .Utils.GEWarmUp import GEWarmUp
from .Utils.GEPlayerTracker import GEPlayerTracker
import random
import GEPlayer, GEUtil, GEMPGameRules, GEGlobal, GEWeapon

USING_API = GEGlobal.API_VERSION_1_2_0

# Created by Euphonic for GoldenEye: Source 5.0
# For more information, visit https://euphonic.dev/goldeneye-source/

#    * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / *
IAmInvincibleVersion = "^uI Am Invincible! ^11.0.0"
#    * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / * / *

class IAmInvincible( GEScenario ):
    PLAYER_BORIS_CHANCES = "Weights the odds of the player being selected as the next Boris"
    PLAYER_BORIS_DAMAGE = "Tracks how much damage the player has done to Boris"
    
    def __init__( self ):
        super( IAmInvincible, self ).__init__()
        
        self.playerTracker = GEPlayerTracker( self )
        
        self.warmupTimer = GEWarmUp( self )
        self.notice_WaitingForPlayers = 0
        self.WaitingForPlayers = True
        
        self.roundActive = False
        
        self.currentBorisPlayer = False

        self.costumeBoris = "boris"

        self.soundError = "Buttons.beep_denied"
        self.soundPoint = "GEGamePlay.Token_Chime"
        self.soundSpeedBoost = "GEGamePlay.Whoosh"
        
        self.radarIconShapeBoris = ""
        self.radarIconColorBoris = GEUtil.Color( 206, 43, 43, 255 )
        self.objectiveColorBoris = GEUtil.Color( 206, 43, 43, 255 )
        self.objectiveTextBoris = "Boris"
        
        self.messageChannel = 0
        self.messageDisplayTime = 6.0
        self.messageXPos = -1
        self.messageYPos = 0.71
        self.newBorisMessageColor = GEUtil.Color( 206, 43, 43, 255 )
        self.newBorisMessageText = "You are now Boris. You are invincible!"
        self.noBorisMessageColor = GEUtil.CColor(220,220,220,255)
        self.noBorisMessageText = "Boris abandoned the match!"
        
        self.isBorisSpeedBoosted = False
        self.speedBoostMultiplier = 1.25
        self.timerBorisSpeedBoost = 0
        self.timerBorisSpeedBoostMax = 30
        
        self.breakpointDamage = 160 #Default max health/armor is 160/160
        
        self.explosionDamageMultiplier = 0.5
        self.borisSelfDamageMultiplier = 0.07
        
    def GetPrintName( self ):
        return "I Am Invincible!"

    def GetScenarioHelp( self, help_obj ):
        help_obj.SetDescription( "Nobody screws with Boris Grishenko!\n\nEach round, one random player is selected as Boris. Boris is invincible!\n\nMI6 players gain points by damaging Boris. Boris gains a point per kill.\n\nBoris's slaps one-shot kill and grant a temporary speed boost.\n\nTeamplay: Always\n\nCreated by Euphonic" )
        help_obj.SetInfo("Nobody Screws With the Invincible Boris Grishenko!", "https://euphonic.dev/goldeneye-source/i-am-invincible")

        pane = help_obj.AddPane( "iaminvincible1" )
        help_obj.AddHelp( pane, "iami_boris", "Boris is invincible!" )
        help_obj.AddHelp( pane, "", "Everyone gangs up on Boris. Damaging him awards points. Boris gets a point per kill.")
        help_obj.AddHelp( pane, "", "Boris's slap attack one-shot kills and grants a temporary speed boost")
        
        help_obj.SetDefaultPane( pane )

    def GetGameDescription( self ):
        return "I Am Invincible!"
    
    def GetTeamPlay( self ):
        return GEGlobal.TEAMPLAY_ALWAYS

    def OnPlayerSay( self, player, text ):
        if text == "!version":
            GEUtil.ClientPrint(None, GEGlobal.HUD_PRINTTALK, IAmInvincibleVersion)

    def OnLoadGamePlay( self ):
        self.CreateCVar( "iami_warmup", "20", "The warmup time in seconds (Use 0 to disable warmup)" )
        GEUtil.PrecacheSound(self.soundError) # Played when attempting to switch to the wrong team
        GEUtil.PrecacheSound(self.soundPoint) # Played when a non-Boris player scores a point
        
        GEMPGameRules.SetExcludedCharacters("jaws,mayday,oddjob,ourumov,samedi,guard,infantry,_random")
    
    def OnUnloadGamePlay( self ):
        GEMPGameRules.SetExcludedCharacters("")
    
    def OnPlayerConnect( self, player ):
        self.playerTracker.SetValue( player, self.PLAYER_BORIS_DAMAGE, 0 )
        self.playerTracker.SetValue( player, self.PLAYER_BORIS_CHANCES, 2 )
    
    def OnPlayerDisconnect( self, player ):
        if self.isBoris(player):
            self.endRoundBorisAbandoned(True)
    
    def CanPlayerChangeChar( self, player, ident ):
        if self.isBoris(player) and ident != self.costumeBoris:
            return False
        else:
            return True
            
    def OnRoundBegin( self ):
        GEMPGameRules.DisableArmorSpawns()
        GEMPGameRules.ResetAllTeamsScores()
        GEMPGameRules.ResetAllPlayersScores()
        
        if GEMPGameRules.GetNumActivePlayers() < 2:
            self.WaitingForPlayers = True
        
        if not self.WaitingForPlayers and not self.warmupTimer.IsInWarmup():
            oldBorisPlayer = self.currentBorisPlayer
            self.selectBoris()
            
            if oldBorisPlayer:
                self.outgoingBorisPlayer(oldBorisPlayer, False)
        
            if self.currentBorisPlayer:
                self.currentBorisPlayer.ChangeTeam(GEGlobal.TEAM_JANUS, True)
                self.currentBorisPlayer.SetPlayerModel( self.costumeBoris, 0 )
        
        for player in GetPlayers():
            self.playerTracker.SetValue( player, self.PLAYER_BORIS_DAMAGE, 0 )
    
    def OnRoundEnd( self ):
        self.isBorisSpeedBoosted = False
        self.timerBorisSpeedBoost = 0
        if self.currentBorisPlayer:
            self.currentBorisPlayer.SetSpeedMultiplier( 1 )
    
    def OnPlayerKilled( self, victim, killer, weapon ):
        if self.warmupTimer.IsInWarmup() or self.WaitingForPlayers or not victim:
            return
        else:
            if self.isBoris(victim):
                victim.AddRoundScore( -5 )
                GEUtil.EmitGameplayEvent( "iami_boris_suicide", "%i" % victim.GetUserID() )
            else:
                GEUtil.EmitGameplayEvent( "iami_killed_by_boris", "%i" % victim.GetUserID() )
                GEUtil.EmitGameplayEvent( "iami_boris_kills", "%i" % victim.GetUserID() )
                GEScenario.OnPlayerKilled( self, victim, killer, weapon )
                weaponName = weapon.GetClassname().replace('weapon_', '').lower()
                
                if self.isBoris(killer) and (weaponName == "slappers" or weaponName == "knife"):
                    GEUtil.PlaySoundToPlayer( killer, self.soundSpeedBoost, False )
                    self.timerBorisSpeedBoost = self.timerBorisSpeedBoostMax
                    GEUtil.EmitGameplayEvent( "iami_boris_slap_kill", "%i" % killer.GetUserID() )
                    if not self.isBorisSpeedBoosted:
                        self.isBorisSpeedBoosted = True
                        killer.SetSpeedMultiplier(self.speedBoostMultiplier)

    def CalculateCustomDamage( self, victim, info, health, armor ):
        attacker = GEPlayer.ToMPPlayer( info.GetAttacker() )
        
        if self.isBoris(victim) and self.isExplosiveDamage(info):
            if self.isBoris(attacker):
                health = health * self.borisSelfDamageMultiplier; armor = armor * self.borisSelfDamageMultiplier
            # We ignore the damage reduction for direct-hit explosions
            elif health + armor != 398.0:
                health = health * self.explosionDamageMultiplier; armor = armor * self.explosionDamageMultiplier
            
        if self.isBoris(victim) and attacker and not self.isBoris(attacker):
            damageTotal = self.playerTracker.GetValue( attacker, self.PLAYER_BORIS_DAMAGE )
            damageTotal += min(health + armor, self.breakpointDamage)
            
            if damageTotal >= self.breakpointDamage:
                damageTotal -= self.breakpointDamage
                attacker.AddRoundScore( 1 )
                GEMPGameRules.GetTeam(GEGlobal.TEAM_MI6).IncrementRoundScore( 1 )
                GEUtil.PlaySoundToPlayer( attacker, self.soundPoint, False )
                GEUtil.EmitGameplayEvent( "iami_damage_point", "%i" % attacker.GetUserID() )
            self.playerTracker.SetValue( attacker, self.PLAYER_BORIS_DAMAGE, damageTotal )
            health = 0; armor = 0
            
        if self.identifyWeapon(info) == "weapon_slappers" and self.isBoris(attacker):
            health = 1000; armor = 1000

        return health, armor
    
    def OnThink( self ):
        if GEMPGameRules.GetNumActivePlayers() < 2:
            if not self.WaitingForPlayers:
                self.notice_WaitingForPlayers = 0
                GEMPGameRules.EndRound(True, True)
                if self.currentBorisPlayer:
                    oldBorisPlayer = self.currentBorisPlayer
                    self.currentBorisPlayer = False
                    self.outgoingBorisPlayer(oldBorisPlayer, True)

            elif GEUtil.GetTime() > self.notice_WaitingForPlayers:
                GEUtil.HudMessage( None, "#GES_GP_WAITING", self.messageXPos, self.messageYPos, GEUtil.Color( 255, 255, 255, 255 ), 2.5, 1 )
                self.notice_WaitingForPlayers = GEUtil.GetTime() + 12.5

            self.warmupTimer.Reset()
            self.WaitingForPlayers = True
            return
        
        elif self.WaitingForPlayers:
            self.WaitingForPlayers = False
            if not self.warmupTimer.HadWarmup():
                self.warmupTimer.StartWarmup( int( GEUtil.GetCVarValue( "iami_warmup" ) ), True )
                GEUtil.EmitGameplayEvent( "iami_startwarmup" )
            else:
                GEMPGameRules.EndRound( False, True )
        
        if self.timerBorisSpeedBoost:
            self.timerBorisSpeedBoost -= 1
        if self.currentBorisPlayer and self.isBorisSpeedBoosted and not self.timerBorisSpeedBoost:
            self.currentBorisPlayer.SetSpeedMultiplier( 1 )
            self.isBorisSpeedBoosted = False
            
        if self.currentBorisPlayer and not self.currentBorisPlayer.IsDead():
            self.giveAllWeapons( self.currentBorisPlayer, False )

    def OnPlayerSpawn( self, player ):
        player.SetSpeedMultiplier( 1.0 )
        # Make sure players are on the right team
        if self.isBoris(player) and player.GetTeamNumber() == GEGlobal.TEAM_MI6:
            player.ChangeTeam(GEGlobal.TEAM_JANUS, True)
        elif not self.isBoris(player) and player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
            player.ChangeTeam(GEGlobal.TEAM_MI6, True)
        
        if self.isBoris(player):
            GEUtil.HudMessage( player, self.newBorisMessageText , self.messageXPos, self.messageYPos, self.newBorisMessageColor, self.messageDisplayTime, self.messageChannel )
            
            GEMPGameRules.GetRadar().AddRadarContact( player, GEGlobal.RADAR_TYPE_PLAYER, True, self.radarIconShapeBoris, self.radarIconColorBoris )
            GEMPGameRules.GetRadar().SetupObjective( player, GEGlobal.TEAM_NONE, "", self.objectiveTextBoris, self.objectiveColorBoris, 0, True )
            
            if player.GetPlayerModel() != self.costumeBoris:
                player.SetPlayerModel( self.costumeBoris, 0 )
            
            self.giveAllWeapons( self.currentBorisPlayer, True )
        
    def CanPlayerChangeTeam( self, player, oldteam, newteam, wasforced ):
        if self.isBoris(player):
            if newteam == GEGlobal.TEAM_MI6:
                player.ChangeTeam(GEGlobal.TEAM_JANUS, True)
                GEUtil.PlaySoundToPlayer( player, self.soundError, False )
                return False
            elif newteam != GEGlobal.TEAM_JANUS:
                self.endRoundBorisAbandoned(False)
        else:
            if newteam == GEGlobal.TEAM_JANUS:
                if oldteam == GEGlobal.TEAM_MI6:
                    GEUtil.PlaySoundToPlayer( player, self.soundError, False )
                else:
                    player.ChangeTeam(GEGlobal.TEAM_MI6, True)
                return False
        return True

    def isBoris( self, player):
        if not player:
            return False
        elif player == self.currentBorisPlayer:
            return True
        else:
            return False
    
    def identifyWeapon( self, info ):
        weaponTemp = info.GetWeapon()
        if weaponTemp != None:
            weapon = GEWeapon.ToGEWeapon( weaponTemp )
            if weapon != None:
                return weapon.GetClassname().lower()
        return "weapon_paintbrush"
    
    def isExplosiveDamage( self, info ):
        if info.GetDamageType() == 64:
            return True
        else:
            return False
    
    def giveAllWeapons( self, player, giveArmor ):
        if giveArmor:
            player.SetArmor(player.GetMaxArmor())
        for i in range(0, 8):
            player.GiveNamedWeapon( GEWeapon.WeaponClassname(GEMPGameRules.GetWeaponInSlot(i)), 800 )
    
    def selectBoris( self ):
        borisLotteryList = []
        for player in GetPlayers():
            if player.GetTeamNumber() != GEGlobal.TEAM_MI6 and player.GetTeamNumber() != GEGlobal.TEAM_JANUS:
                continue
            else:
                if self.isBoris(player):
                    playerEntries = 0
                else:
                    playerEntries = max(self.playerTracker.GetValue( player, self.PLAYER_BORIS_CHANCES ), 1)
                
                borisLotteryList += [player] * playerEntries
                self.playerTracker.SetValue( player, self.PLAYER_BORIS_CHANCES, playerEntries + 1)
        
        if borisLotteryList:
            self.currentBorisPlayer = random.choice(borisLotteryList)
            GEUtil.EmitGameplayEvent( "iami_new_boris", "%i" % self.currentBorisPlayer.GetUserID() )
    
    def outgoingBorisPlayer( self, player, notEnoughPlayers = False ):
        if player.GetTeamNumber() == GEGlobal.TEAM_JANUS:
            player.ChangeTeam(GEGlobal.TEAM_MI6, True)
            if notEnoughPlayers:
                self.playerTracker.SetValue( player, self.PLAYER_BORIS_CHANCES, max(self.playerTracker.GetValue( player, self.PLAYER_BORIS_CHANCES), 3 ) )
    
    def endRoundBorisAbandoned( self, disconnected):
        GEUtil.HudMessage( None, self.noBorisMessageText , self.messageXPos, self.messageYPos, self.noBorisMessageColor, self.messageDisplayTime, self.messageChannel )
        GEMPGameRules.EndRound(True, True)
        if not disconnected:
            self.playerTracker.SetValue( self.currentBorisPlayer, self.PLAYER_BORIS_CHANCES, -2)
        self.currentBorisPlayer = False