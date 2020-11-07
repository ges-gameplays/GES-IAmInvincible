from .bot_deathmatch import bot_deathmatch
from .Schedules import Cond
import GEGlobal as Glb

USING_API = Glb.API_VERSION_1_1_0

class bot_iaminvincible( bot_deathmatch ):
    def GatherConditions( self ):
        bot_deathmatch.GatherConditions( self )
        self.ClearCondition( Cond.GES_CLOSE_TO_ARMOR )
        self.ClearCondition( Cond.GES_CAN_SEEK_ARMOR )
        self.SetCondition( Cond.GES_CAN_NOT_SEEK_ARMOR )

    def bot_WeaponParamCallback( self ):
        params = bot_deathmatch.bot_WeaponParamCallback( self )
        params["melee_bonus"] = -5
        return params
