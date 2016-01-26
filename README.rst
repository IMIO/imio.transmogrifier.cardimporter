==========================================================================
imio.transmogrifier.cardimporter
==========================================================================

Transform old association or shop types into new collective.directory.card type.
The script create collective.directory.directory and collective.directory.category to stock new cards


Add new blueprint thanks in @@pipeline-config :
    
    ...
    referencesimporter
    cardimporter
    TTGoogleMapMarkerToCard
    propertiesimporter
    ...
    
[cardimporter]
blueprint = imio.transmogrifier.cardimporter.cardimporter

[TTGoogleMapMarkerToCard]
blueprint = imio.transmogrifier.cardimporter.TTGoogleMapMarkerToCard    