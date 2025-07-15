"""
消息类型集合。

定义了所有支持的消息类型常量。
"""
class Msg:
    """消息类型集合。

    包含所有支持的消息类型常量。
    """
    # 基础消息类型
    AtAll = "AtAll"  # 艾特全体成员
    AtUin = "AtUin"  # 被艾特账号
    AtName = "AtName"  # 被艾特昵称
    Id = "Id"  # ID
    Ok = "Ok"  # 状态码
    No = "No"  # 状态码
    Op = "Op"  # 操作
    OpUid = "OpUid"  # 操作
    All = "All"  # 所有
    Get = "Get"  # 得到
    Gif = "Gif"  # 动图
    Img = "Img"  # 图片
    Ptt = "Ptt"  # 语音
    Uid = "Uid"  # 账号
    Uin = "Uin"  # 账号
    Url = "Url"  # 链接
    Xml = "Xml"  # XML
    Code = "Code"  # 码
    Info = "Info"  # 信息
    Json = "Json"  # JSON
    Text = "Text"  # 文本消息
    Temp = "Temp"  # 临时消息
    Time = "Time"  # 时间
    Type = "Type"  # 类型
    Emoid = "Emoid"  # 表情id
    Flash = "Flash"  # 闪图
    MsgId = "MsgId"  # 消息id
    Reply = "Reply"  # 回复
    Title = "Title"  # 用户头衔
    Value = "Value"  # 值
    Audio = "Audio"  # 音频
    Video = "Video"  # 视频
    Width = "Width"  # 宽度
    Bubble = "Bubble"  # 气泡id
    Height = "Height"  # 高度
    Notice = "Notice"  # 公告
    People = "People"  # 人数
    Refresh = "Refresh"  # 刷新
    UinName = "UinName"  # 名称 备注.....
    UinNick = "UinNick"  # 昵称
    Typeface = "Typeface"  # 字体
    Withdraw = "Withdraw"  # 撤回
    OpName = "OpName"  # 操作者名字
    OpNick = "OpNick"  # 操作者昵称
    Agree = "Agree"  # 同意
    Refuse = "Refuse"  # 拒绝
    Ignore = "Ignore"  # 忽略
    Account = "Account"  # 登录账号
    Open = "Open"  # 打开
    Close = "Close"  # 关闭
    MD5 = "MD5"  # MD5
    Size = "Size"  # 大小
    Offset = "Offset"  # 开始
    Add = "Add"  # 增加
    Remove = "Remove"  # 移除
    Seq = "Seq"  # 序号
    EmojiFace = "EmojiFace"  # 小黄脸表情
    EmojiSuper = "EmojiSuper"  # 超级表情
    EmojiSuperQQ = "EmojiSuperQQ"  # [超级QQ秀表情]OK
    ProgressPush = "ProgressPush"  # 进度推送
    PokeID = "PokeID"  # 戳一戳id
    PokeIDSub = "PokeIDSub"  # 戳一戳子id
    PokeMsg = "PokeMsg"  # 戳一戳消息
    PokeSize = "PokeSize"  # 戳一戳大小
    Dice = "Dice"  # 骰子
    WindowJitter = "WindowJitter"  # 窗口抖动
    FlashWord = "FlashWord"  # 闪字
    FingerGuess = "FingerGuess"  # 猜拳
    HeadPortrait = "HeadPortrait"  # 头像
    AppId = "AppId"  # 账号

    # 合并转发消息
    MultiMsg = "MultiMsg"  # 消息合并转发
    MultiMsgGet = "MultiMsgGet"  # 消息合并转发 获取
    MultiMsgPut = "MultiMsgPut"  # 消息合并转发 保存

    # 好友相关
    Friend = "Friend"  # 好友消息
    FriendListDisable = "FriendListDisable"  # 好友禁用列表
    FriendListGet = "FriendListGet"  # 获取好友列表
    FriendListGetName = "FriendListGetName"  # 获取好友备注
    FriendListGetNick = "FriendListGetNick"  # 获取好友昵称
    FriendBeatABeat = "FriendBeatABeat"  # 好友拍一拍
    FriendMsgCacheGet = "FriendMsgCacheGet"  # 获取好友消息缓存

    # 群聊相关
    Group = "Group"  # 群聊消息
    Owner = "Owner"  # 群主/频道主 QQ
    GroupId = "GroupId"  # 群号
    GroupName = "GroupName"  # 群名
    GroupListDisable = "GroupListDisable"  # 群聊禁用列表
    GroupListGet = "GroupListGet"  # 获取群聊列表
    GroupListGetName = "GroupListGetName"  # 获取群聊名称
    GroupMemberListGet = "GroupMemberListGet"  # 获取群聊成员列表
    GroupMemberListGetAdmin = "GroupMemberListGetAdmin"  # 获取群聊管理员列表
    GroupMemberListGetInactive = "GroupMemberListGetInactive"  # 获取群聊成员不活跃列表
    GroupMemberListGetProhibit = "GroupMemberListGetProhibit"  # 获取群聊成员被禁言列表
    GroupMemberListGetInfo = "GroupMemberListGetInfo"  # 获取群聊成员信息
    GroupMemberSignout = "GroupMemberSignout"  # 群聊成员退出
    GroupMemberNickModify = "GroupMemberNickModify"  # 修改群聊成员昵称
    GroupModifyAdmin = "GroupModifyAdmin"  # 群聊管理员修改
    GroupModifySpecialTitle = "GroupModifySpecialTitle"  # 修改群聊专属头衔
    GroupNotify = "GroupNotify"  # 群通知
    GroupProhibitAll = "GroupProhibitAll"  # 群聊全体禁言
    GroupProhibitMember = "GroupProhibitMember"  # 群聊成员禁言
    GroupMsgCacheGet = "GroupMsgCacheGet"  # 获取群聊消息缓存
    GroupMsgAnonymous = "GroupMsgAnonymous"  # 群聊消息匿名
    GroupMsgSetNotDisturb = "GroupMsgSetNotDisturb"  # 设置群聊消息免打扰
    GroupAnonymous = "GroupAnonymous"  # 群聊匿名开关变动
    GroupEnterState = "GroupEnterState"  # 进群状态
    GroupInvitationFriend = "GroupInvitationFriend"  # 邀请好友进群
    GroupNewMember = "GroupNewMember"  # 群聊新成员进群通知
    GroupMusic = "GroupMusic"  # 一起听歌开关变动
    GroupBeatABeat = "GroupBeatABeat"  # 群聊拍一拍
    GroupEssence = "GroupEssence"  # 群聊精华
    GroupDissolut = "GroupDissolut"  # 群聊解散
    GroupClockin = "GroupClockin"  # 群聊打卡

    # 群文件相关
    GroupFile = "GroupFile"  # 群文件
    GroupFileListGet = "GroupFileListGet"  # 获取列表
    GroupFileUpload = "GroupFileUpload"  # 上传文件
    GroupFileCreate = "GroupFileCreate"  # 创建文件夹
    GroupFileRemove = "GroupFileRemove"  # 删除文件
    GroupFileRemoveFolder = "GroupFileRemoveFolder"  # 删除文件夹
    GroupFileMove = "GroupFileMove"  # 移动文件
    GroupFileRename = "GroupFileRename"  # 重命名文件夹

    GroupStick = "GroupStick"  # 群帖子

    # 频道相关
    Guild = "Guild"  # 频道消息
    TinyId = "TinyId"  # 频道用户id
    GuildId = "GuildId"  # 频道id
    GuildCode = "GuildCode"  # 频道id号
    ChannelId = "ChannelId"  # 频道id子
    GuildType = "GuildType"  # 频道type
    GuildName = "GuildName"  # 频道名
    ChannelName = "ChannelName"  # 频道名子
    GuildMsgCacheGet = "GuildMsgCacheGet"  # 获取频道消息缓存
    GuildMemberSignout = "GuildMemberSignout"  # 频道成员退出
    GuildEssence = "GuildEssence"  # 频道精华

    # 系统相关
    System = "System"  # 系统消息
    Online = "Online"  # 查询在线状态
    Goline = "Goline"  # 账号上线
    GolineRetry = "GolineRetry"  # 重新上线
    Offline = "Offline"  # 账号下线
    GolineWindows = "GolineWindows"  # Windows端账号上线
    OfflineWindows = "OfflineWindows"  # Windows端账号下线
    Heartbeat = "Heartbeat"  # 心跳消息
    HeartbeatLong = "HeartbeatLong"  # 长连心跳消息
    FavoriteCard = "FavoriteCard"  # 名片赞
    FavoriteCardListGet = "FavoriteCardListGet"  # 名片赞列表获取
    FavoritePersonSign = "FavoritePersonSign"  # 个性签名赞
    NewFriendNotify = "NewFriendNotify"  # 新朋友通知
    UserSearch = "UserSearch"  # 搜索
    UserInfoGet = "UserInfoGet"  # 获取上线信息
    UserInfoModify = "UserInfoModify"  # 修改用户信息
    UserGroupJoin = "UserGroupJoin"  # 加群
    UserGroupSignout = "UserGroupSignout"  # 退群
    UserFriendAdd = "UserFriendAdd"  # 加好友
    UserFriendRemove = "UserFriendRemove"  # 删除好友
    UserSigninDay = "UserSigninDay"  # 日签卡打卡
    UserSigninNight = "UserSigninNight"  # 晚安卡打卡
    OntimeTask = "OntimeTask"  # 整点任务
    GolineMode = "GolineMode"  # 上线模式

    # 空间相关
    Qzone = "Qzone"  # 空间消息
    SaySay = "SaySay"  # 说说

    # 用户信息相关
    Skey = "Skey"  # Skey
    Age = "Age"  # 年龄
    Gender = "Gender"  # 性别
    Nick = "Nick"  # 昵称
    Name = "Name"  # 备注
    MemberLevel = "MemberLevel"  # 成员等级
    JoinTime = "JoinTime"  # 加入时间
    LastSpeakTime = "LastSpeakTime"  # 最后发言时间
    SpecialTitle = "SpecialTitle"  # 专属头衔
    Level = "Level"  # 等级
    Location = "Location"  # 地区

    # 系统功能
    Debug = "Debug"  # 调试模式
    CacheNewFile = "CacheNewFile"  # 获取临时文件
    Unauthorized = "Unauthorized"  # 未授权
    OicqWebScanCodeLogin = "OicqWebScanCodeLogin"  # 网站扫码登录

    # JSON消息类型
    SignJson = "SignJson"  # 签名卡片
    CustomJson = "CustomJson"  # 自定义JSON消息
    JSON_KG = "JSON_KG"  # 酷狗音乐
    JSON_WY = "JSON_WY"  # 网易云音乐
    JSON_QQ = "JSON_QQ"  # QQ音乐
    JSON_KW = "JSON_KW"  # 酷我音乐
    JSON_JSHU = "JSON_JSHU"  # 简书
    JSON_BAIDU = "JSON_BAIDU"  # 百度
    JSON_YK = "JSON_YK"  # 优酷
    JSON_IQY = "JSON_IQY"  # 爱奇艺
    JSON_BD = "JSON_BD"  # 波点
    JSON_BL = "JSON_BL"  # 哔哩哔哩
    JSON_KS = "JSON_KS"  # 快手
    JSON_MG = "JSON_MG"  # 咪咕
    JSON_QQLLQ = "JSON_QQLLQ"  # QQ浏览器
    JSON_QQKJ = "JSON_QQKJ"  # QQ空间
    JSON_5SING = "JSON_5SING"  # 5SING

    # 日志打印
    PrintE = "PrintE"  # 错误日志
    PrintI = "PrintI"  # 信息日志
    PrintV = "PrintV"  # 详细日志
    PrintW = "PrintW"  # 警告日志

    # 上线模式
    GM_PO = "PO"  # 官方人机
    GM_PA = "PA"  # 安卓手机
    GM_PP = "PP"  # 安卓平板
    GM_PL = "PL"  # 企鹅密码
    GM_SA = "SA"  # 安卓手表(扫码登陆)
    GM_SL = "SL"  # 企鹅扫码(扫码登陆)