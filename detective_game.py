#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
庄园晚宴谋杀案 —— 一个命令行推理游戏
=========================================
你是受邀调查林家庄园命案的侦探。
通过「探索房间」收集物证、「询问嫌疑人」获取口供，
用排除法锁定：凶手 / 凶器 / 案发房间。
最终用「指认」提交你的推理。
"""

import textwrap
import sys

# ---------------------------------------------------------------------------
# 案件设定（真相）
# ---------------------------------------------------------------------------
SOLUTION = {
    "murderer": "赵天成",   # 商业伙伴
    "weapon": "毒酒",       # 酒窖取出的 1982 红酒
    "room": "酒窖",         # 案发地点
}

# 可探索的房间：访问后得到物证线索
ROOMS = {
    "餐厅": {
        "desc": "长桌上杯盘狼藉，死者右手边的高脚杯还残留着暗红液体。",
        "clue": (
            "【物证·餐厅】化验显示死者酒杯里有「乌头碱」残留 —— 他是被毒死的，"
            "凶器是一杯下了毒的红酒，而非利器或钝器。"
        ),
        "eliminates": {"weapon": ["烛台", "刀", "绳索", "镇纸"]},
    },
    "书房": {
        "desc": "壁炉旁的镇纸、书桌上的文件。死者生前在这里处理生意。",
        "clue": (
            "【物证·书房】书桌上摊着一份借款合同：赵天成欠林国栋 500 万，下月到期。"
            "书桌上的青铜镇纸一尘不染，没有血迹，也不含毒。"
        ),
        "eliminates": {"weapon": ["镇纸"]},
    },
    "温室": {
        "desc": "玻璃花房里摆着园艺剪刀和一卷麻绳，泥土湿润。",
        "clue": (
            "【物证·温室】园艺剪刀与麻绳都干干净净，没有血迹，也不在餐厅酒杯的使用场景里。"
            "园丁说他整晚都在这儿，且看见秘书苏婉在书房。"
        ),
        "eliminates": {"weapon": ["绳索", "刀"]},
    },
    "酒窖": {
        "desc": "阴凉的地下酒窖，一格格橡木架摆满藏酒，监控探头闪着红灯。",
        "clue": (
            "【物证·酒窖】一瓶 1982 年的红酒被新开过，瓶口检测出乌头碱。"
            "监控记录显示：22:00 赵天成独自进入酒窖，22:25 才出来。"
        ),
        "eliminates": {"room": ["餐厅", "书房", "温室", "卧室"], "weapon": ["烛台"]},
    },
    "卧室": {
        "desc": "死者的卧室，床头柜上摊着一本日记。",
        "clue": (
            "【物证·卧室】死者日记写道：『有人扬言要让我身败名裂，我已在遗嘱里做了防备。』"
            "日记未提及任何暴力冲突，卧室里也没有打斗痕迹。"
        ),
        "eliminates": {"room": ["卧室"]},
    },
}

# 可询问的嫌疑人：访谈后得到口供与不在场信息
SUSPECTS = {
    "老周": {
        "role": "管家",
        "alibi": (
            "【口供·管家老周】老周在厨房盯着晚宴收尾。厨房监控显示 21:30 到 23:00 他一直在厨房，"
            "没有离开过，因此不可能出现在酒窖下毒。"
        ),
        "eliminates": {"murderer": ["老周"]},
    },
    "林若曦": {
        "role": "独女",
        "alibi": (
            "【口供·林若曦】死者的女儿。通话记录显示 22:00–22:40 她一直在房间打长途电话，"
            "有多人可作证，没有作案时间。"
        ),
        "eliminates": {"murderer": ["林若曦"]},
    },
    "苏婉": {
        "role": "私人秘书",
        "alibi": (
            "【口供·苏婉】秘书。园丁在温室看见她 21:45–22:50 一直在书房整理文件，"
            "与温室物证互相印证，她那段时间不在酒窖。"
        ),
        "eliminates": {"murderer": ["苏婉"]},
    },
    "阿强": {
        "role": "园丁",
        "alibi": (
            "【口供·阿强】新来的园丁。他整晚待在温室，并反过来证实了秘书苏婉的行踪。"
            "温室里的绳索、剪刀都无血迹，他的嫌疑最小。"
        ),
        "eliminates": {"murderer": ["阿强"]},
    },
    "赵天成": {
        "role": "商业伙伴",
        "alibi": (
            "【口供·赵天成】死者的合伙人。他承认 22:00 进过酒窖『取了瓶酒』，却说不清具体拿了哪瓶。"
            "他欠死者 500 万即将到期，动机最强，且那段时间无人能为他作证。"
        ),
        "eliminates": {},  # 关键嫌疑人，不被任何人排除
    },
}

ALL_WEAPONS = ["烛台", "刀", "绳索", "镇纸", "毒酒"]
ALL_ROOMS = list(ROOMS.keys())


# ---------------------------------------------------------------------------
# 游戏状态
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.visited_rooms = set()
        self.interviewed = set()
        self.eliminated = {
            "murderer": set(),
            "weapon": set(),
            "room": set(),
        }
        self.actions = 0

    def print_rules(self):
        print(textwrap.dedent("""
        ============ 庄园晚宴谋杀案 ============
        富商林国栋（林老爷）昨晚死于自家庄园，死亡时间约 22:30。
        你是被请来的侦探。要破案，必须同时锁定三件事：
          1) 凶手是谁   2) 凶器是什么   3) 案发在哪个房间

        可用指令：
          探索 <房间>    例如：探索 酒窖
          询问 <嫌疑人>  例如：询问 赵天成
          线索            查看你的侦探笔记本（已掌握的物证与排除项）
          帮助            重新显示本说明
          指认            提交你的推理结论
          退出            结束游戏

        嫌疑人：老周 / 林若曦 / 苏婉 / 阿强 / 赵天成
        房间：餐厅 / 书房 / 温室 / 酒窖 / 卧室
        ========================================
        """))

    def explore(self, room):
        if room not in ROOMS:
            print(f"没有「{room}」这个房间。可探索：{ '、'.join(ROOMS) }")
            return
        self.actions += 1
        if room in self.visited_rooms:
            print(f"你再次查看{room}：{ROOMS[room]['desc']}（线索已记录）")
            return
        self.visited_rooms.add(room)
        info = ROOMS[room]
        print(f"\n📍 {room}\n{info['desc']}\n→ {info['clue']}")
        self._apply_eliminations(info.get("eliminates", {}))
        self._suggest_next()

    def interview(self, name):
        if name not in SUSPECTS:
            print(f"没有「{name}」这个嫌疑人。可询问：{ '、'.join(SUSPECTS) }")
            return
        self.actions += 1
        if name in self.interviewed:
            print(f"你又找{name}聊了聊，但他说的还是那些。（口供已记录）")
            return
        self.interviewed.add(name)
        info = SUSPECTS[name]
        print(f"\n🗣 {name}（{info['role']}）\n→ {info['alibi']}")
        self._apply_eliminations(info.get("eliminates", {}))
        self._suggest_next()

    def _apply_eliminations(self, elim):
        for category, items in elim.items():
            for it in items:
                self.eliminated[category].add(it)

    def _suggest_next(self):
        unvisited = [r for r in ROOMS if r not in self.visited_rooms]
        unmet = [s for s in SUSPECTS if s not in self.interviewed]
        tips = []
        if unvisited:
            tips.append(f"还有房间可探索：{ '、'.join(unvisited) }")
        if unmet:
            tips.append(f"还可询问：{ '、'.join(unmet) }")
        if tips:
            print("💡 " + "；".join(tips))

    def show_notebook(self):
        print("\n📓 侦探笔记本")
        print("— 物证 / 口供已收集 —")
        if not self.visited_rooms and not self.interviewed:
            print("（还什么都没查。先用「探索」和「询问」收集线索吧。）")
        for r in ROOMS:
            if r in self.visited_rooms:
                print(f"  ✔ 探索过 {r}")
        for s in SUSPECTS:
            if s in self.interviewed:
                print(f"  ✔ 询问过 {s}")
        print("— 已排除项（排除法） —")
        print(f"  凶手：{ '、'.join(sorted(self.eliminated['murderer'])) or '（暂无）' }")
        print(f"  凶器：{ '、'.join(sorted(self.eliminated['weapon'])) or '（暂无）' }")
        print(f"  房间：{ '、'.join(sorted(self.eliminated['room'])) or '（暂无）' }")
        remain_m = [m for m in SUSPECTS if m not in self.eliminated['murderer']]
        remain_w = [w for w in ALL_WEAPONS if w not in self.eliminated['weapon']]
        remain_r = [r for r in ALL_ROOMS if r not in self.eliminated['room']]
        print("— 剩余嫌疑人 —")
        print(f"  凶手候选：{ '、'.join(remain_m) or '（全部排除，请检查线索）' }")
        print(f"  凶器候选：{ '、'.join(remain_w) or '（全部排除，请检查线索）' }")
        print(f"  房间候选：{ '、'.join(remain_r) or '（全部排除，请检查线索）' }")

    def accuse(self):
        print("\n🔍 最终指认")
        print("请分别说出你的结论（直接输入名字，回车确认）。")
        m = self._pick("凶手是谁", list(SUSPECTS))
        w = self._pick("凶器是什么", ALL_WEAPONS)
        r = self._pick("案发在哪个房间", ALL_ROOMS)
        if None in (m, w, r):
            print("指认取消。")
            return
        print(f"\n你的推理：{m} 在 {r} 用 {w} 杀害了林国栋。")
        correct = (m == SOLUTION["murderer"] and
                   w == SOLUTION["weapon"] and
                   r == SOLUTION["room"])
        if correct:
            print("\n🎉 推理正确！真相大白 ——")
            print(f"  商业伙伴赵天成因 500 万债务走投无路，在酒窖取出 1982 年红酒")
            print(f"  下毒（乌头碱），趁晚宴后无人注意让林国栋饮下，致其中毒身亡。")
            print(f"  你共用了 {self.actions} 个调查动作，是一位敏锐的侦探！")
            sys.exit(0)
        else:
            wrong = []
            if m != SOLUTION["murderer"]:
                wrong.append("凶手")
            if w != SOLUTION["weapon"]:
                wrong.append("凶器")
            if r != SOLUTION["room"]:
                wrong.append("案发房间")
            print(f"\n❌ 指认错误。你的判断在 { '、'.join(wrong) } 上出了偏差。")
            print("回去再核对线索与不在场证明，排除法能帮你锁定真相。")
            print("（输入「线索」查看笔记本，或继续「探索」「询问」。想重来可退出后重启。）")

    def _pick(self, prompt, options):
        while True:
            val = input(f"  {prompt}？可选 { '、'.join(options) } ：").strip()
            if val == "":
                return None
            if val in options:
                return val
            print(f"  「{val}」不在选项里，请重新输入。")


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------
def main():
    game = Game()
    game.print_rules()
    print("\n提示：先「探索」所有房间、「询问」所有嫌疑人，再用「线索」做排除，最后「指认」。\n")
    while True:
        try:
            cmd = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见，侦探。")
            break
        if not cmd:
            continue
        parts = cmd.split(maxsplit=1)
        head = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if head in ("帮助", "help", "?"):
            game.print_rules()
        elif head in ("探索", "查看", "去"):
            game.explore(arg)
        elif head in ("询问", "访谈", "找"):
            game.interview(arg)
        elif head in ("线索", "笔记本", "笔记"):
            game.show_notebook()
        elif head in ("指认", "accuse"):
            game.accuse()
        elif head in ("退出", "exit", "quit", "q"):
            print("侦探离开庄园，案件未结。随时可以回来。")
            break
        else:
            print("看不懂这条指令。输入「帮助」查看可用指令。")


if __name__ == "__main__":
    main()
