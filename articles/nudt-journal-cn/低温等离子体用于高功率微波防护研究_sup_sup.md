# 低温等离子体用于高功率微波防护研究<sup></sup>

Published: Unknown

Source: http://journal.nudt.edu.cn/gfkjdxxb/article/html/202306011?tab=abstract

低温等离子体用于高功率微波防护研究<sup></sup>
EI•CA•INSPEC•JST•SCOPUS
中文核心期刊•CSCD•WJCI
首页
期刊介绍
投稿指南
来稿须知
稿件要求
录用修订
稿件流程
相关下载
编委会
出版声明
出版道德声明
出版伦理声明
开放获取声明
联系我们
期刊订阅
纸刊订阅
E-mail订阅
Rss
AI检索
Deepseek
豆包
文心一言
通义
讯飞星火
Kimi
English
AI智能辅读
本章节主要描述了高功率微波攻击方式对电子信息系统安全构成的巨大威胁，可能改变未来战争的作战样式和战争形态。美、俄、英、日、法等国高度重视这一领域，美国已投入使用的装备包括主动拒止系统、警惕鹰系统、携带高功率微波弹头的AGM-86巡航导弹及用于空域封锁的高功率微波炮，并继续加大在该领域的研发投入。针对高功率微波攻击，目前基于固态半导体器件的电路级防护能力有限，主要适用于数千瓦以内的脉冲功率，而频率选择表面、能量选择表面和等离子体被认为是可能的防护方法。其中，等离子体具有敏感性，能随入射高功率微波强度改变状态，影响入射波传输。该章节对等离子体在高功率微波防护中的应用进行了仿真与实验分析，研究了柱状等离子体阵列与高功率微波相互作用的物理过程和机理，并通过实验验证了其防护效果，同时总结了基于等离子体的高功率微波防护技术需解决的主要问题。
1 基本理论
本章节主要描述了为了研究高功率微波作用下等离子体产生的电磁屏蔽效应，采用流体近似方法进行仿真分析。通过波动方程对电磁波在密度均匀的等离子体中的传播过程进行了表征，考虑了电场强度、磁场强度、入射波角频率以及真空和等离子体中相关物理常数的影响。同时，利用电子传递方程分析了外加电磁场所导致的等离子体内电子密度变化，涉及电子迁移率、电子扩散率及由内部碰撞反应引起的电子产生与消失源项。此外，还通过重物质传递方程探讨了电磁场对其他带电粒子分布的影响，包括第k种粒子的摩尔分数、气体密度、平均流体速率及其扩散通量等参数的变化。
2 仿真计算模型
本章节主要描述了采用COMSOL软件构建的一个仿真计算模型，该模型旨在模拟电磁波通过空气介质和等离子体介质后的传播过程。模型设置中，电磁波从上边界进入并向下传播，最终在完美匹配层被完全吸收，以防止反射产生的二次激励影响结果准确性。等离子体层由多根柱状等离子体单元组成，这些单元紧密排列且参数一致。仿真条件设定了入射电磁波的场强E
0
和频率f，并选择惰性气体Ar作为工作气体，具体气体压强为P，所涉及的粒子种类及碰撞反应见表1。
3 仿真计算结果分析
本章节主要描述了假设初始气体温度为300K、压强400Pa条件下，电子均匀分布密度1.0×10
16
m
-3
的等离子体在高功率微波作用下的仿真计算结果。研究中使用的等离子体直径25mm，玻璃管壁厚度0.3mm，初始电子能为3eV，碰撞频率5×10
9
Hz，入射微波频率6GHz、电场强度2×10
6
V/m。仿真结果显示，在t=2.15×10
-10
s时，等离子体区域的电场与空气区域基本一致，表明初始时刻入射波可无损透过等离子体；而在t=3.98×10
-10
s至t=5.99×10
-10
s期间，上下方空气区域的电场值变化显著，说明此阶段内等离子体与高功率微波发生了剧烈相互作用；到了t=9.03×10
-10
s到t=0.001s时，等离子体上方出现驻波场，下方电场几乎为零，显示出强烈的电磁屏蔽特性。进一步分析表明，在高功率微波的作用下，等离子体内电子经历加速、非弹性碰撞、雪崩效应和新的粒子平衡建立的过程，导致等离子体的电磁参数发生变化，从而表现出类似于金属的屏蔽效果，实现了对入射高功率微波的有效防护。
4 实验验证
本章节主要描述了实验设备连接示意图：高功率微波信号由L波段高功率微波源产生，经定向耦合器分成两路。一路作为参考信号接入高精度示波器；另一路由发射喇叭辐射后通过柱状等离子体阵列被接收喇叭接收，并最终作为接收信号接入高精度示波器。实验中使用的等离子体采用高频辉光放电方式产生，初始平均电子密度约为1.2×10
16
m
-3
。实验使用了1.3GHz的高功率微波源，脉冲宽度为1000ns。在等离子体未开启时，接收信号与参考信号基本一致；而在等离子体开启后，高功率微波透射衰减超过20dB，表明等离子体对高功率微波具有显著的防护作用。进一步实验显示双层等离子体可使高功率微波透射衰减值超过26dB，证实了增加等离子体厚度能提升防护效果。然而，该实验为初步探索，在极化方式、微波频率、等离子体状态等方面尚需进一步研究和完善。
5 结论
本章节总结了基于等离子体流体近似方法建立的高功率微波与等离子体相互作用仿真计算模型，研究了入射电场随时间演变的过程，并分析了等离子体防护高功率微波的机理。仿真结果显示，当高功率微波通过等离子体时会被吸收并引发电子雪崩，产生更高密度的等离子体，导致对高功率微波的反射效应增强，直至仅有少量能量进入等离子体维持后续电子。随着微波能量继续增大，这一过程会重复发生直到新的动态平衡形成；当微波消失后，等离子体会快速恢复到初始状态。研究还探讨了高功率微波频率、脉宽、等离子体初始电子密度和放电气体种类等因素对相互作用的影响。实验通过高频辉光放电产生柱状等离子体阵列验证了其对高功率微波的有效防护作用，并致力于开发小型化等离子体防护器件，解决包括不影响低功率电磁信号传输、缩短非线性效应响应时间、拓宽响应频率以及提高装置抗高功率微波能力等问题。
* 以上内容由AI自动生成，内容仅供参考。对于因使用本网站以上内容产生的相关后果，本网站不承担任何商业和法律责任
AI智能问答
1：等离子体如何用于防护高功率微波攻击？
2：在高功率微波作用下，等离子体中的哪些方程被用来表征电磁波的传播过程和带电粒子的行为？
3：仿真计算模型中使用了什么软件进行电磁波传播模拟？
4：高功率微波对等离子体电磁特性有何影响？
5：等离子体对高功率微波的防护效果如何？
6：高功率微波与等离子体相互作用会产生什么效应？
* 以上内容由AI自动生成，内容仅供参考。对于因使用本网站以上内容产生的相关后果，本网站不承担任何商业和法律责任
AI语音讲解
Pause
Play
% buffered
00:00
00:00
07:32
Unmute
Mute
Disable captions
Enable captions
PIP
Exit fullscreen
Enter fullscreen
Play
* 以上内容由AI自动生成，内容仅供参考。对于因使用本网站以上内容产生的相关后果，本网站不承担任何商业和法律责任
引用本文:
李志刚,邱志楠,汪家春,等.低温等离子体用于高功率微波防护研究<sup></sup>[J].国防科技大学学报,2023,45(6):84-89.
Citation:
LI Zhigang, QIU Zhinan, WANG Jiachun, et al. Study of high-power microwave protection technology based on low-temperature plasma[J]. Journal of National University of Defense Technology,2023,45(6):84-89.
低温等离子体用于高功率微波防护研究
*
doi:
10.11887/j.cn.202306012
李志刚
角色:
第一作者
机构:
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
邮箱:
class1_48@163.com；
简介:
李志刚（1990—），男，山东济宁人，副研究员，博士，E-mail: class1_48@163.com；
，
 邱志楠
机构:
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
，
 汪家春
机构:
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
，
 刘丽萍
机构:
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
，
 王俊儒
机构:
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
，
 陈宗胜
角色:
通信作者
机构:
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
邮箱:
chenzongsh12@163.com
简介:
陈宗胜，男，安徽合肥人，副研究员，博士，E-mail: chenzongsh12@163.com
国防科技大学 脉冲功率激光技术国家重点实验室, 安徽 合肥 230037
基金项目:
安徽省自然科学基金面上资助项目（1908085MF205）
详细信息
收起信息
作者简介
李志刚（1990—），男，山东济宁人，副研究员，博士，E-mail: class1_48@163.com；
通信作者
陈宗胜，男，安徽合肥人，副研究员，博士，E-mail: chenzongsh12@163.com
中图分类号:
TN01
文献标志码:
A
文章编号:
1001-2486(2023)06-084-06
Study of high-power microwave protection technology based on low-temperature plasma
LI Zhigang
Role:
First Author
Affiliation:
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
Email:
class1_48@163.com；
，
 QIU Zhinan
Affiliation:
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
，
 WANG Jiachun
Affiliation:
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
，
 LIU Liping
Affiliation:
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
，
 WANG Junru
Affiliation:
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
，
 CHEN Zongsheng
Role:
Corresponding Author
Affiliation:
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
Email:
chenzongsh12@163.com
State Key Laboratory of Pulsed Power Laser Technology, National University of Defense Technology, Hefei 230037 , China
摘要
HTML全文
图(6)表(1)
参考文献(12)
相似文献
出版信息
访问统计
资源附件
摘要
等离子体对于高功率微波的攻击具有独特的防护效果。基于等离子体流体近似方法，利用COMSOL软件研究了高功率微波与柱状等离子体阵列相互作用过程中入射电场随时间的演变过程，分析了等离子体防护高功率微波的物理过程和作用机理。研究结果表明，入射的高功率微波会使等离子体参数发生剧烈变化，特别是其电子密度将急剧增加，从而使等离子体对入射的高功率微波表现出类似金属的电磁特性，最终实现对入射高功率微波的有效防护。此外，利用高频辉光放电产生柱状等离子体阵列，通过实验验证了等离子体对高功率微波的防护作用。最后，总结了基于等离子体的高功率微波防护技术需解决的主要问题。
关键词
高功率微波
/
防护技术
/
柱状等离子体阵列
Abstract
Plasma has a unique protective effect against high-power microwave attack. Based on the plasma fluid approximation method, the time dependent evolution of the incident electric field during the interaction between high-power microwaves and columnar plasma arrays was studied by using COMSOL software, and the physical process and mechanism of plasma protection against high-power microwaves were analyzed. The results show that the incident high-power microwave will change the plasma parameters drastically, especially the electron density will increase sharply, so that the plasma will show metal-like electromagnetic properties to the incident high-power microwave, and finally realize the effective protection against the incident high-power microwave. In addition, the plasma protection against high-power microwaves was experimentally verified by using columnar plasma arrays generated by high-frequency glow discharge. Finally, the main problems to be solved for plasma-based high-power microwave protection technology were summarized.
Keywords
high-power microwave
/
protection technology
/
columnar plasma arrays
1 基本理论
1.1 波动方程
1.2 电子传递方程
1.3 重物质传递方程
2 仿真计算模型
3 仿真计算结果分析
4 实验验证
4.1 实验方案
4.2 实验结果
5 结论
高功率微波攻击方式的出现给电子信息系统安全带来了巨大的威胁。在未来信息化条件下，电子信息系统一旦遭受破坏，再强大的武器装备也会变成“瞎子”“聋子”，甚至变为一堆废铁。可见，高功率微波攻击或将改变未来战争的作战样式，对未来战争形态产生重大影响
[
1
]
。
正是认识到高功率微波攻击的强大作战效能，美、俄、英、日、法等国都非常重视，并已有相关装备报道。以美国为例，已投入使用的装备有主动拒止系统、警惕鹰系统、携带高功率微波弹头的AGM-86巡航导弹以及用于空域封锁的高功率微波炮等
[
2
]
。目前，美军在这一领域仍在继续加大投入。因此，提升装备对高功率微波的防护能力具有重要的军事效益和现实意义。
目前基于固态半导体器件的电路级防护，其能防护的最大脉冲功率一般在数千瓦以内（具体数值与微波脉冲的宽度有关）。对于更高功率的微波脉冲，可能的防护方法主要有频率选择表面、能量选择表面和等离子体
[
3
-
5
]
。其中等离子体对高功率微波的能量具有敏感性，能够随着入射高功率微波的强弱改变自身的状态，进而影响入射波的传输，兼具了频率选择表面和能量选择表面的优点，具有很好的研究价值和应用前景
[
6
-
8
]
。
本文针对等离子体对高功率微波的防护效果开展了仿真与实验分析，研究了高功率微波与柱状等离子体阵列相互作用过程中入射电场随时间的演变过程，分析了等离子体防护高功率微波的物理过程和作用机理；在此基础上，通过实验验证了等离子体对高功率微波的防护效果；最后结合相关研究工作，对基于等离子体的高功率微波防护技术需解决的主要问题进行了总结。
1 基本理论
为了研究在高功率微波作用下等离子体产生的电磁屏蔽作用，本文采用流体近似方法
[
9
-
10
]
进行仿真分析，分别采用等离子体中的波动方程、电子传递方程和重物质传递方程，对高功率微波在等离子体中的传播过程和等离子体内部电子及其他带电粒子受入射电磁能量的影响进行表征。
1.1 波动方程
当电磁波入射到密度均匀的等离子体上时，电磁波在等离子体中的麦克斯韦方程
[
11
]
为：
∇
×
H
=
j
ω
ε
0
ε
r
⋅
E
(1)
∇
×
E
=
-
j
ω
μ
0
H
(2)
可得波动方程：
∇
×
∇
×
E
-
k
0
2
ε
r
⋅
E
=
0
(3)
其中：
H
为磁场强度；
E
为电场强度；
ω
为入射波的角频率；
ε
0
、
μ
0
、
k
0
分别为真空中的介电常数、磁导率和波数；
ε
r
为等离子体的相对介电常数，可通过式（4）求解。
ε
r
=
1
-
ω
p
ω
(
ω
-
i
v
)
(4)
式中，
ω
p
为等离子频率，
υ
为电子碰撞频率，
i
为复数标号。
1.2 电子传递方程
在外加电磁场的作用下，等离子体内部电子密度的变化可通过电子传递方程来进行分析，方程可表示为：
∂
∂
t
n
e
+
∇
⋅
Γ
e
=
R
e
(5)
Γ
e
=
-
μ
e
⋅
E
n
e
-
D
e
⋅
∇
n
e
(6)
其中：
n
e
为电子数密度；
μ
e
、
D
e
为电子迁移率和电子扩散率；
R
e
为电子源项，表征了内部碰撞反应导致的电子的产生与消失，可通过式（7）求得。
R
e
=
∑
j
=
1
M
x
j
k
j
N
n
n
e
(7)
式中，
x
j
为
j
反应中碰撞粒子的摩尔质量分数，
k
j
为
j
反应的反应速率，
N
n
为等离子体中总的粒子数密度。
1.3 重物质传递方程
外加电磁场还会引发等离子体内部其他带电粒子的分布产生变化，可通过重物质传递方程来进行分析，方程为：
ρ
∂
∂
t
ω
k
+
ρ
(
u
⋅
∇
)
ω
k
=
∇
⋅
j
k
+
R
k
(8)
式中：
ω
k
为第
k
种粒子的摩尔分数；
ρ
为气体密度；
u
为平均流体速率；
j
k
为第
k
种粒子的扩散通量，可通过式（9）表示。
j
k
=
ρ
ω
k
V
k
(9)
V
k
=
D
k
,
m
∇
ω
k
ω
k
+
D
k
,
m
∇
M
n
M
n
+
D
k
T
ρ
ω
k
∇
T
T
-
z
k
μ
k
,
m
E
(10)
式中，
D
k
，
m
为重物质平均扩散系数，
M
n
为重物质平均摩尔质量，
D
T
k
、
z
k
、
μ
k，m
分别为第
k
种粒子的热扩散系数、电荷数以及平均迁移率，
T
为气体温度。
2 仿真计算模型
采用COMSOL软件进行计算，具体模型如
图1
所示。模型模拟的物理过程为：电磁波从上边界进入模型，向下传播，经空气介质和等离子体介质后，传输至设置的完美匹配层（避免波反射产生的二次激励）被完全吸收。等离子体层由多根前后延伸的柱状等离子体单元紧密排列组成，假设每根等离子体单元的参数完全一致。
图
1
高功率微波与柱状等离子体阵列相互作用的仿真计算模型示意图
Fig.
1
Simulation schematic diagram of the interactions between high-power microwave and columnar plasma arrays
假设入射电磁波场强为
E
0
，电磁波频率为
f
，选择常用的惰性气体Ar作为工作气体，所涉及的粒子种类和碰撞反应在
表1
给出
[
12
]
，气体压强为
P
。
表
1
氩等离子体内部碰撞反应方程及类型
Table
1
Collision reaction functions and types inside Ar plasma
3 仿真计算结果分析
假设初始时刻气体温度为300 K，压强为400 Pa，电子初始为均匀分布，密度为1.0×10
16
m
-3
，等离子体直径为25 mm，玻璃管壁厚度为0.3 mm，初始电子能为3 eV，碰撞频率为5×10
9
Hz，高功率微波频率为6 GHz，电场强度为2×10
6
V/m，极化方向与等离子体管轴向方向一致，计算时间设置为0~0.001 s。
图2
为不同时刻计算模型中的电场分布，图中采用统一的颜色图例（
E
：0~4×10
6
V/m）。高功率微波脉冲从上边界入射，经空气层和等离子体层后被完美匹配层吸收。
从
图2
可以看出，在
t
=2.15×10
-10
s时刻，等离子体区域的电场值与上下空气区域基本一致，说明在初始时刻入射波几乎可以无损透过等离子体区域。从
t
=3.98×10
-10
s到
t
=5.99×10
-10
s，可以明显看到等离子体下方空气区域的电场值越来越小，上方空气电场峰值不断增大。说明这一时间内，等离子体与高功率微波发生了剧烈的相互作用。从
t
=9.03×10
-10
s到
t
=0.001 s可以看到，等离子体上方区域存在明显的驻波场，下方区域仅有很少的能量透过，电场值接近于零，等离子体类似于金属，对入射电磁波表现出较强的屏蔽特性。
为了更好地解释上述结果的产生原因，
图3
给出了计算模型中轴线电子密度和电场分布的演变曲线，图中灰色区域代表玻璃放电管的物理尺寸。
图3
中表征的物理过程可描述为：①初始阶段，等离子体内部电子受到高功率微波的加速作用，由低能电子转化为高能电子，并通过弹性碰撞反应，将吸收的电磁能量传递给中性粒子，提高等离子体的内能，在这一阶段非弹性碰撞反应并不显著，电子密度增加缓慢，等离子体本身的电磁参数基本保持不变，入射波几乎无损透过等离子体区域；②随着高能电子不断积累和等离子体内能不断增加，等离子体中非弹性碰撞反应速率显著增大，大量的高能电子被消耗，平均电子能急剧下降，电子雪崩效应产生，大量新生电子参与到等离子体振荡中，等离子体电导率急剧增大，对入射波的衰减急剧增大，等离子体电磁特性发生较大改变，其对入射波的屏蔽作用开始显现，透过等离子体区域的电磁能量不断减小；③当高能电子被大量消耗，直接电离反应（见
表1
中反应4）开始减弱，间接电离反应（见
表1
中反应5）增强，激发态氩原子被大量消耗用于继续产生新的带电粒子，等离子体电磁特性进一步发生改变，电导率继续增大，入射波在等离子体中趋肤深度不断减小，等离子体对入射波的屏蔽性能更为显著，透过等离子体区域的电磁能量进一步减小；④随着等离子体区域电子密度不断增加，入射的电磁能量除小部分被吸收外，大部分被反射，等离子体内部碰撞反应趋于缓和，电子密度增加速率变缓，空间分布开始变得均匀，等离子体内部逐渐达到新的平衡。
图
2
计算模型中电场强度空间分布随激励时间的演变过程
Fig.
2
Time dependence of the electric field intensity in simulation calculation model
图
3
模型中轴线电子密度和电场分布随激励时间的演变过程
Fig.
3
Time dependence of the axial electron density and electric field distribution in simulation calculation model
从粒子平衡角度对这一过程进行解释：等离子体与高功率微波之间的相互作用是通过状态改变来维持粒子平衡的。等离子体作为特殊的介质，内部存在一定的粒子平衡，并且具有强烈维持这一平衡的意愿。高功率微波的入射破坏了等离子体中的粒子平衡，等离子体内部随之产生强烈的振荡和碰撞反应，建立新的状态来平衡外加电磁场产生的影响。
从上面的物理过程分析可知，入射的高功率微波会使等离子体的参数发生剧烈变化，特别是其电子密度将急剧增加，这会引起等离子体电磁参数发生同步改变，从而使等离子体对入射的高功率微波表现出类似金属的电磁特性，最终实现对入射高功率微波的有效防护。
4 实验验证
4.1 实验方案
图4
为实验设备连接示意图。实验中，高功率微波信号由L波段高功率微波源产生，经定向耦合器后分成两路信号：一路信号经同轴线缆接入高精度示波器，作为参考信号；另一路信号通过同轴线缆传输至发射喇叭以产生高功率微波辐射信号，高功率辐射波传输通过等离子体阵列后被接收喇叭接收，而后经衰减器、检波器、同轴线缆接入高精度示波器，作为接收信号。柱状等离子体阵列与收发喇叭口面平行，距离发射喇叭3 m（满足远场条件），紧贴接收喇叭并使等离子体单元完全覆盖整个接收喇叭口面，从而能够保证到达等离子体阵列处的高功率微波功率密度与到达接收口面的功率密度相一致。等离子体采用高频辉光放电方式产生，其初始平均电子密度约为1.2×10
16
m
-3
。
图
4
实验测试示意图
Fig.
4
Schematic diagram of the experimental test
4.2 实验结果
实验采用1.3 GHz高功率微波源，脉冲宽度为1 000 ns。
图5
为脉冲源发射功率为170 kW时（此时辐照到等离子体上的电场强度约为8 100 V/m），等离子体未开启情况下的测试结果，其中黄色线为发射端输入的参考信号测试结果，绿色线为接收信号测试结果。
图6
为脉冲源发射功率约为144 kW时（此时辐照到等离子体上的电场强度约为7 450 V/m），等离子体开启情况下的测试结果。对比
图5
和
图6
可以看出，等离子体对1.3 GHz高功率微波产生了明显的防护作用（透射衰减大于20 dB）。
图
5
发射功率为170 kW、等离子体未开启情况下的测试结果
Fig.
5
Test results in condition of emission power 170 kW, plasma turned off
实验过程中还对同样条件下的双层等离子体进行了防护验证，高功率微波透射衰减值超过26 dB，显然，等离子体厚度越大，防护效果越好。另外，由于是初步探索实验，在设置上缺少了对极化方式、微波频率、等离子体状态等多因素的考虑，在后续的研究工作中将进一步完善。
图
6
发射功率为144 kW、等离子体开启情况下的测试结果
Fig.
6
Test results in condition of emission power 144 kW, plasma turned on
5 结论
本文基于等离子体流体近似方法，建立了高功率微波与等离子体相互作用仿真计算模型，研究了高功率微波与柱状等离子体阵列相互作用过程中入射电场随时间的演变过程，分析了等离子体防护高功率微波的机理和物理过程。仿真结果表明，高功率微波通过等离子体时，会被后者吸收造成电子雪崩，产生更高电子密度的等离子体，使得等离子体对高功率微波的反射效应不断增强。这一过程不断发生，直至仅能有少量的微波能量进入等离子体，用于后产生电子的维持。此后，当进入等离子体中的微波能量继续增大时，电子雪崩效应再次发生，电子密度也会相应继续增大，直至达到新的动态平衡；而当高功率微波消失时，由于缺乏外界能量维持，电子和离子迅速复合，等离子体迅速恢复到与高功率微波相互作用前的状态。同时，利用本文建立的模型，还可以对高功率微波与等离子体相互作用过程中的影响因素（如高功率微波频率、脉宽、等离子体初始电子密度、初始电子能量、放电气体种类和气压等）进行分析。
此外，利用高频辉光放电产生柱状等离子体阵列，通过实验证实了等离子体对高功率微波具有很好的防护作用。目前正在开展基于等离子体的高功率微波小型化防护器件研究，主要解决的问题有：①对于被保护电子系统工作频带内的小功率电磁信号，防护器件不能影响其正常传输；②在高功率微波作用下，等离子体发生非线性效应的时间尽可能短，以免造成漏过微波功率过大问题；③等离子体产生非线性效应的响应频率要尽可能宽；④等离子体产生装置自身能经得起高功率微波的攻击，同时其体积、质量和功耗满足使用要求。
图
1
高功率微波与柱状等离子体阵列相互作用的仿真计算模型示意图
Fig.
1
Simulation schematic diagram of the interactions between high-power microwave and columnar plasma arrays
下载:
全尺寸图片
(44)
图
2
计算模型中电场强度空间分布随激励时间的演变过程
Fig.
2
Time dependence of the electric field intensity in simulation calculation model
下载:
全尺寸图片
(80)
图
3
模型中轴线电子密度和电场分布随激励时间的演变过程
Fig.
3
Time dependence of the axial electron density and electric field distribution in simulation calculation model
下载:
全尺寸图片
(82)
图
4
实验测试示意图
Fig.
4
Schematic diagram of the experimental test
下载:
全尺寸图片
(94)
图
5
发射功率为170 kW、等离子体未开启情况下的测试结果
Fig.
5
Test results in condition of emission power 170 kW, plasma turned off
下载:
全尺寸图片
(46)
图
6
发射功率为144 kW、等离子体开启情况下的测试结果
Fig.
6
Test results in condition of emission power 144 kW, plasma turned on
下载:
全尺寸图片
(66)
表
1
氩等离子体内部碰撞反应方程及类型
Table
1
Collision reaction functions and types inside Ar plasma
下载:
全尺寸图片
(49)
图
1
高功率微波与柱状等离子体阵列相互作用的仿真计算模型示意图
Fig.
1
Simulation schematic diagram of the interactions between high-power microwave and columnar plasma arrays
图
2
计算模型中电场强度空间分布随激励时间的演变过程
Fig.
2
Time dependence of the electric field intensity in simulation calculation model
图
3
模型中轴线电子密度和电场分布随激励时间的演变过程
Fig.
3
Time dependence of the axial electron density and electric field distribution in simulation calculation model
图
4
实验测试示意图
Fig.
4
Schematic diagram of the experimental test
图
5
发射功率为170 kW、等离子体未开启情况下的测试结果
Fig.
5
Test results in condition of emission power 170 kW, plasma turned off
图
6
发射功率为144 kW、等离子体开启情况下的测试结果
Fig.
6
Test results in condition of emission power 144 kW, plasma turned on
表
1
氩等离子体内部碰撞反应方程及类型
Table
1
Collision reaction functions and types inside Ar plasma
[1]
刘振林, 杨光, 段难, 等. 高功率微波导弹对战场环境的影响及对抗技术研究[J]. 微波学报, 2020, 36(增刊1): 358-361.
LIU Z L, YANG G, DUAN N, et al. Research on the impact of CHAMP on the battlefield environment and the countermeasure technology[J]. Journal of Microwaves, 2020, 36(Suppl 1): 358-361.(in Chinese)
[2]
冯奇, 傅镇波. 高功率微波武器典型场景应用分析[J]. 中国电子科学研究院学报, 2021, 16(9): 916-920.
FENG Q, FU Z B. Application analysis of HPM weapon in typical scenarios[J]. Journal of China Academy of Electronics and Information Technology, 2021, 16(9): 916-920.(in Chinese)
[3]
刘洋, 程立. 电磁脉冲防护技术研究现状[J]. 材料导报, 2016, 30(增刊2): 272-275.
LIU Y, CHENG L. Research status of electromagnetic pulse weapon and its protection technology[J]. Materials Review, 2016, 30(Suppl 2): 272-275.(in Chinese)
[4]
宋玮, 邵浩, 张治强, 等. 射频击穿等离子体对高功率微波传输特性的影响[J]. 物理学报, 2014, 63(6): 158-162.
SONG W, SHAO H, ZHANG Z Q, et al. High power microwave propagation properties in radio frequency breakdown plasma[J]. Acta Physica Sinica, 2014, 63(6): 158-162.(in Chinese)
[5]
KOURTZANIDIS K, BOEUF J P, ROGIER F. Three dimensional simulations of pattern formation during high-pressure, freely localized microwave breakdown in air[J]. Physics of Plasmas, 2014, 21(12): 123513.
[6]
赵朋程, 郭立新, 李慧敏.110 GHz高功率微波在大气击穿等离子体中的传输、反射和吸收[J]. 电波科学学报, 2016, 31(3): 512-515.
ZHAO P C, GUO L X, LI H M. Transmission, reflection and absorption of 110 GHz high-power microwave in air breakdown plasma[J]. Chinese Journal of Radio Science, 2016, 31(3): 512-515.(in Chinese)
[7]
PAYNE K, XU K, CHOI J H, et al. Multiphysics analysis of plasma-based tunable absorber for high-power microwave applications[J]. IEEE Transactions on Antennas and Propagation, 2021, 69(11): 7624-7636.
[8]
WANG H Y, HU F, HU B, et al. Characteristics of microwave breakdown in cavity filter under high power microwave environment[C]//Proceedings of 2020 IEEE MTT-S International Conference on Numerical Electromagnetic and Multiphysics Modeling and Optimization(NEMO), 2020.
[9]
郑灵, 赵青, 罗先刚, 等. 等离子体中电磁波传输特性理论与实验研究[J]. 物理学报, 2012, 61(15): 343-349.
ZHENG L, ZHAO Q, LUO X G, et al. Theoretical and experimental studies of electromagnetic wave transmission in plasma[J]. Acta Physica Sinica, 2012, 61(15): 343-349.(in Chinese)
[10]
李志刚, 陈宗胜. 等离子体与高功率微波相互作用中电子分布特性[J]. 国防科技大学学报, 2020, 42(1): 10-17.
LI Z G, CHEN Z S. Distributions of the electron in the interactions between high power microwave and plasma[J]. Journal of National University of Defense Technology, 2020, 42(1): 10-17.(in Chinese)
[11]
袁忠才, 时家明. 高功率微波与等离子体相互作用理论和数值研究[J]. 物理学报, 2014, 63(9): 255-264.
YUAN Z C, SHI J M. Theoretical and numerical studies on interactions between high-power microwave and plasma[J]. Acta Physica Sinica, 2014, 63(9): 255-264.(in Chinese)
[12]
HE W, LIU X H, XIAN R C, et al. Kinetics characteristics and bremsstrahlung of argon DC discharge under atmospheric pressure[J]. Plasma Science and Technology, 2013, 15(4): 335-342.
[1]
李志刚,邱志楠,汪家春,刘丽萍,王俊儒,陈宗胜.
低温等离子体用于高功率微波防护研究
[J].国防科技大学学报,2023,45(6):84-89.
[2]
李永忠,张亚洲,赫崇峻.
用于高功率微波测量的电磁探针研究
[J].国防科技大学学报,1999,21(5):72-74.
[3]
李志刚,陈宗胜.
等离子体与高功率微波相互作用中电子分布特性
[J].国防科技大学学报,2020,42(1):10-17.
[4]
刘洋,程立,汪家春,袁忠才,时家明.
核电磁脉冲模拟器的电场特性及等离子体阵列的防护性能
[J].国防科技大学学报,2018,40(4):41-46.
[5]
李志刚,程立,马志伟,汪家春,时家明.
入射频率对高功率微波与等离子体相互作用的影响分析
[J].国防科技大学学报,2018,40(4):47-52.
[6]
王贵林,张飞虎.
微波铁氧体基片精密研抛技术研究
[J].国防科技大学学报,2007,29(3):113-117.
[7]
张存波.
微波脉冲对硅基双极型晶体管的损伤特性（高功率微波技术研究所专题组稿）
[J].国防科技大学学报,2015,37(2).
[8]
林峥.
高功率微波技术在军事上的应用
[J].军事电子,1994(5):1-5.
[9]
陈凯柏,周晓东,高敏.
毫米波引信高功率微波前门耦合效应研究
[J].兵器装备工程学报,2020,41(2).
[10]
李战国 胡真闫学锋,孙小亮.
等离子体技术在核化生洗消中的应用研究
[J].防化研究,2007(2):61-64.
[11]
王运华.
微波消解预处理技术用于食品微量元素分析的研究
[J].兵团教育学院学报,2002,12(1):71-72.
[12]
刘春明.
光学仪器综合封存防护技术研究
[J].军械工程学院学报,1993(2).
[13]
令钧溥,王蕾,皮明瑶,贺军涛,陈冬群,王朗宁.
美国反无人机高功率微波技术研究现状及启示
[J].国防科技,2023(3):74-80.
[14]
王忠春,向红军,纵兆春.
基于高压脉冲等离子体技术的TNT废水处理研究
[J].军械工程学院学报,2013(4):75-78.
[15]
吴新贺,党方超.
高功率微波空间相干合成基本原理与技术挑战
[J].国防科技,2022(3):9-14.
[16]
复杂战场环境导弹发射装置隐身防护技术研究
[J].现代防御技术
[17]
曹哲,柴振海,高红卫,鲁耀兵.
分布式阵列相参合成雷达技术研究与试验
[J].现代防御技术,2012,40(4):1-11.
[18]
王鹏,彭博,窦林涛.
相控阵雷达外场试验目标模拟技术研究
[J].指挥控制与仿真,2014,36(3).
[19]
舒楠,张厚,李圭源,徐海洋.
X波段雷达前门防护技术研究
[J].现代防御技术,2011,39(1):138-140,156.
[20]
郑翠娥,孙大军,张殿伦.
一种基于超短基线的高精度多目标水声定位技术研究
[J].海军工程大学学报,2007,19(2):12-16.
PDF下载
XML下载
导出引用
引用提醒
图(6)
/
表(1)
手机扫码阅读
引用本文
李志刚,邱志楠,汪家春,等.低温等离子体用于高功率微波防护研究<sup></sup>[J].国防科技大学学报,2023,45(6):84-89.
复制
LI Zhigang, QIU Zhinan, WANG Jiachun, et al. Study of high-power microwave protection technology based on low-temperature plasma[J]. Journal of National University of Defense Technology,2023,45(6):84-89.
Copy
计量
文章访问量:
28801
HTML全文浏览量:
3510
PDF下载量:
9895
被引次数:
图
1
高功率微波与柱状等离子体阵列相互作用的仿真计算模型示意图
Fig.
1
Simulation schematic diagram of the interactions between high-power microwave and columnar plasma arrays
图
2
计算模型中电场强度空间分布随激励时间的演变过程
Fig.
2
Time dependence of the electric field intensity in simulation calculation model
图
3
模型中轴线电子密度和电场分布随激励时间的演变过程
Fig.
3
Time dependence of the axial electron density and electric field distribution in simulation calculation model
图
4
实验测试示意图
Fig.
4
Schematic diagram of the experimental test
图
5
发射功率为170 kW、等离子体未开启情况下的测试结果
Fig.
5
Test results in condition of emission power 170 kW, plasma turned off
图
6
发射功率为144 kW、等离子体开启情况下的测试结果
Fig.
6
Test results in condition of emission power 144 kW, plasma turned on
表
1
氩等离子体内部碰撞反应方程及类型
Table
1
Collision reaction functions and types inside Ar plasma
刘振林, 杨光, 段难, 等. 高功率微波导弹对战场环境的影响及对抗技术研究[J]. 微波学报,2020,36(增刊1):358-361.
LIU Z L, YANG G, DUAN N,et al. Research on the impact of CHAMP on the battlefield environment and the countermeasure technology[J]. Journal of Microwaves,2020,36(Suppl 1):358-361.(in Chinese)
冯奇, 傅镇波. 高功率微波武器典型场景应用分析[J]. 中国电子科学研究院学报,2021,16(9):916-920.
FENG Q, FU Z B. Application analysis of HPM weapon in typical scenarios[J]. Journal of China Academy of Electronics and Information Technology,2021,16(9):916-920.(in Chinese)
刘洋, 程立. 电磁脉冲防护技术研究现状[J]. 材料导报,2016,30(增刊2):272-275.
LIU Y, CHENG L. Research status of electromagnetic pulse weapon and its protection technology[J]. Materials Review,2016,30(Suppl 2):272-275.(in Chinese)
宋玮, 邵浩, 张治强, 等. 射频击穿等离子体对高功率微波传输特性的影响[J]. 物理学报,2014,63(6):158-162.
SONG W, SHAO H, ZHANG Z Q,et al. High power microwave propagation properties in radio frequency breakdown plasma[J]. Acta Physica Sinica,2014,63(6):158-162.(in Chinese)
KOURTZANIDIS K, BOEUF J P, ROGIER F. Three dimensional simulations of pattern formation during high-pressure,freely localized microwave breakdown in air[J]. Physics of Plasmas,2014,21(12):123513.
赵朋程, 郭立新, 李慧敏.110 GHz高功率微波在大气击穿等离子体中的传输、反射和吸收[J]. 电波科学学报,2016,31(3):512-515.
ZHAO P C, GUO L X, LI H M. Transmission,reflection and absorption of 110 GHz high-power microwave in air breakdown plasma[J]. Chinese Journal of Radio Science,2016,31(3):512-515.(in Chinese)
PAYNE K, XU K, CHOI J H,et al. Multiphysics analysis of plasma-based tunable absorber for high-power microwave applications[J]. IEEE Transactions on Antennas and Propagation,2021,69(11):7624-7636.
WANG H Y, HU F, HU B,et al. Characteristics of microwave breakdown in cavity filter under high power microwave environment[C]//Proceedings of 2020 IEEE MTT-S International Conference on Numerical Electromagnetic and Multiphysics Modeling and Optimization(NEMO),2020.
郑灵, 赵青, 罗先刚, 等. 等离子体中电磁波传输特性理论与实验研究[J]. 物理学报,2012,61(15):343-349.
ZHENG L, ZHAO Q, LUO X G,et al. Theoretical and experimental studies of electromagnetic wave transmission in plasma[J]. Acta Physica Sinica,2012,61(15):343-349.(in Chinese)
李志刚, 陈宗胜. 等离子体与高功率微波相互作用中电子分布特性[J]. 国防科技大学学报,2020,42(1):10-17.
LI Z G, CHEN Z S. Distributions of the electron in the interactions between high power microwave and plasma[J]. Journal of National University of Defense Technology,2020,42(1):10-17.(in Chinese)
袁忠才, 时家明. 高功率微波与等离子体相互作用理论和数值研究[J]. 物理学报,2014,63(9):255-264.
YUAN Z C, SHI J M. Theoretical and numerical studies on interactions between high-power microwave and plasma[J]. Acta Physica Sinica,2014,63(9):255-264.(in Chinese)
HE W, LIU X H, XIAN R C,et al. Kinetics characteristics and bremsstrahlung of argon DC discharge under atmospheric pressure[J]. Plasma Science and Technology,2013,15(4):335-342.
作者投稿
投稿指南
联系我们
公众号
返回顶部
扫码关注
官方微信
您是今天第
7428
位访客
总访问量：
245949704
电话：
0731-87028030
邮箱:journal@nudt.edu.cn
地址：湖南省长沙市开福区德雅路109号
邮政编码：410073
备案号 
：
湘ICP备09019258号
技术支持：北京勤云科技发展有限公司
