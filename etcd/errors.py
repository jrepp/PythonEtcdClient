
# Error codes from coreos/etcd/error.go
KeyNotFound             = 100
TestFailed              = 101
NotFile                 = 102
NoMorePeer              = 103
NotDir                  = 104
NodeExist               = 105
KeyIsPreserved          = 106
RootROnly               = 107
DirNotEmpty             = 108
ExistingPeerAddr        = 109
Unauthorized            = 110

ValueRequired           = 200
PrevValueRequired       = 201
TTLNaN                  = 202
IndexNaN                = 203
ValueOrTTLRequired      = 204
TimeoutNaN              = 205
NameRequired            = 206
IndexOrValueRequired    = 207
IndexValueMutex         = 208
InvalidField            = 209
InvalidForm             = 210
RefreshValue            = 211
RefreshTTLRequired      = 212

RaftInternal            = 300
LeaderElect             = 301

WatcherCleared          = 400
EventIndexCleared       = 401
StandbyInternal         = 402
InvalidActiveSize       = 403
InvalidRemoveDelay      = 404

ClientInternal          = 500

