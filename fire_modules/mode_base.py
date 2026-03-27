#   name=AKAI FL Studio Fire - Mode Base Class
#   Classe de base dont héritent les 4 modes (StepSeq, Note, Drum, Perf)

class FireModeBase:
    """Classe de base pour tous les modes du Akai Fire.
    Chaque mode hérite de cette classe et implémente ses propres handlers."""

    def __init__(self, fire_device):
        self.fire = fire_device

    def OnMidiMsg(self, event):
        """Appelé quand un message MIDI est reçu dans ce mode.
        À surcharger dans les sous-classes."""
        pass

    def OnPadEvent(self, event, pad_num):
        """Appelé quand un pad est pressé/relâché dans ce mode.
        À surcharger dans les sous-classes."""
        pass

    def OnJogWheel(self, event):
        """Appelé quand le jog wheel est tourné dans ce mode.
        À surcharger dans les sous-classes."""
        pass

    def Refresh(self):
        """Rafraîchit l'affichage des pads pour ce mode.
        À surcharger dans les sous-classes."""
        pass

    def OnDisplayZone(self):
        """Met à jour la zone d'affichage dans la playlist.
        À surcharger dans les sous-classes."""
        pass

    def OnActivate(self):
        """Appelé quand ce mode devient actif.
        À surcharger dans les sous-classes."""
        pass

    def OnDeactivate(self):
        """Appelé quand on quitte ce mode.
        À surcharger dans les sous-classes."""
        pass
