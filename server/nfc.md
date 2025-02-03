## 数据格式如下：

```
[ HTTP POST ]
Request: http://192.168.5.18:5000/api/tasks/nfc_post
POST parameters :
名称: card_id / 值: 1(int类型 填入 )
名称: type / 值: TASK(NFC卡类型)
名称: player_id / 值: 0(int类型 按照NFC卡片设计)
名称: id / 值: 1(int类型 )
名称: value / 值: 0(int类型 )
名称: device / 值: {SERIAL}(字符串)
```

## NFC交互设计
NFC卡制作分为三步 ，第一部在系统中录入卡片信息，第二步将相应信息写入NFC卡，第三步系统首次接收到卡片请求视为激活卡片。
NFC_卡片状态 status：未启用 BAN  待激活 INACTIVE；已激活 ACTIVE；已使用 USED
NFC字段设计
```
card_id:NFC卡的标识
type:ID//NFC卡类型： ID 身份卡 TASK 任务卡  MEDAL 成就卡 Points 积分变更卡 CARD 道具卡
Player_ID:标识该卡片的使用对象，0则所有玩家都能使用
ID:根据type类型决定是任务ID还是玩家ID还是成就ID或者是积分变更的玩家ID或者是道具卡ID
value：数值，卡片数量或者是积分变更的数值
DEVICE：//存储的设备标识IMEI用于判断设备是否可信 只有可信设备的数据才进行验证 暂未启用
```
修改/api/tasks/nfc_post接口功能，根据读取到的json数据进行任务处理：接收到的数据中，type字段表示NFC卡片类型，ID表示道具的识别标志；value表示具体的数值；
1、如果type值为ID，则表明该NFC卡是身份识别卡，将player的值返回前端，前端修改playerId值，根据playerid值重新请求数据；
2、如果type值为TASK，表明这是任务卡片，先检查tasks表，根据任务ID检查任务的is_enabled值，如果是0弹窗提示任务未启用，如果是1再检查任务在player_task表中是否存在，不存在则将任务存入player_task表中并将task_status设置为IN_PROGRESS；存在则检查任务状态task_status，如果状态是IN_PROGRESS,且need_check字段为0,则提示完成任务，将状态改为COMPLETE；如果need_check字段为1,将状态改为CHECK;如果任务状态是COMPLETE，提示任务已经完成，如果状态是REJECT，提示任务被驳回以及驳回原因，如果状态是CHECK，提示任务已提交正在检查中
3、如果type值为POINTS,检查NFC_CARD中该卡片是否激活，然后在points_record表中添加积分变更记录，更新player_data表中对应玩家的积分字段points
4、如果type值为CARD，则为用户发放道具卡片，将game_card表中的对应id条目的卡片添加到player_game_card表中，找到player_id和game_card_id与接收到的数据相同的条目，根据value值更新number字段
5、如果type值为MEDAL，则从medals表中查找id为value的值的勋章，将其添加到player_medal表中。