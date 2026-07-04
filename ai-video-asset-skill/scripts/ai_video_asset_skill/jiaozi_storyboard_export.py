"""Export selected reference frames as a JiaoziStudio storyboard script."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .file_manager import (
    EXPORT_DIR_NAME,
    MARKET_MINING_DIR_NAME,
    RESEARCH_DIR_NAME,
    SELECTED_REFERENCE_DIR_NAME,
    ensure_dir,
    read_json,
    relative_path,
    write_json,
    write_text,
)


DEFAULT_TOPIC = "商务人士 签约成功 合作握手 商务宣传片素材"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1k"
DEFAULT_SHOT_DURATION = 4

SECTION_LABELS = [
    "主体",
    "背景",
    "构图",
    "视角/镜头",
    "光线",
    "色彩",
    "风格",
    "材质与细节",
    "情绪氛围",
]

SHOT_ROLE_SET = {
    "establishing",
    "main_subject",
    "process_action",
    "detail_closeup",
    "people_usage",
    "transition_mood",
    "outcome_emotion",
    "end_copy_space",
}


STORY_ARCS: List[Dict[str, Any]] = [
    {
        "group": "01_城市商务开场",
        "purpose": "建立现代企业合作语境和高端商务质感",
        "preferred_categories": ["city", "silhouette", "office", "team"],
        "beats": [
            ("城市商务楼宇晨光开场", "现代城市商务楼宇与玻璃幕墙办公区", "晨光从高层建筑和会议空间外侧进入，建立企业级合作氛围", "远景，宽幅建立镜头，主体建筑占画面中部，留出天空和玻璃反射层次", "缓慢推近"),
            ("高层会议窗前剪影", "几位商务人士在落地窗前形成剪影", "人物面向彼此准备会面，窗外城市光线穿透画面", "中远景，人物横向排布，窗框形成强透视线", "轻微横移"),
            ("办公楼前抵达", "深色西装商务团队抵达现代办公楼", "团队从入口处走入画面，准备进入合作会议", "中景，主体位于画面中央偏左，前景留有玻璃反光", "稳定跟拍"),
            ("电梯厅会前交流", "两三位商务人士在明亮办公楼电梯厅短暂交流", "一人手持资料夹，其他人自然点头回应", "中景，竖向建筑线条强调秩序感", "缓慢推近"),
            ("走廊前往会议室", "商务团队沿玻璃走廊走向会议室", "人物步伐平稳，画面从公共空间转入正式会谈空间", "纵深构图，走廊线条引导视线到远处会议门口", "低速跟随"),
            ("会议室门口握手预热", "两位商务人士在会议室门口礼貌握手", "双方身后各有团队成员，气氛克制专业", "中景，握手动作位于画面视觉中心", "轻微推近"),
            ("城市玻璃反射转场", "玻璃幕墙中的商务人物倒影和城市天际线", "倒影把企业环境与合作主题连接起来", "近中景，玻璃反射占前景，人物轮廓在中景", "缓慢横移"),
            ("会议桌空镜准备", "干净现代会议室和整齐摆放的文件资料", "桌面文件、签字笔和水杯形成签约前的秩序感", "宽幅中景，会议桌从前景延伸到背景", "缓慢推入"),
            ("团队入座建立关系", "多位商务人士围绕会议桌入座", "双方团队各坐一侧，准备开始合作沟通", "中远景，左右阵营清晰，桌面作为稳定横向线", "轻微摇移"),
            ("开场主视觉", "明亮会议室中的核心商务团队", "画面集中呈现合作双方进入正式议题前的专业状态", "宽幅中景，人物集中在画面中央，背景玻璃和窗光保持通透", "缓慢推近"),
        ],
    },
    {
        "group": "02_会前准备与资料确认",
        "purpose": "表现合作前的资料准备、方案确认和专业可信度",
        "preferred_categories": ["document", "tablet", "signing", "office"],
        "beats": [
            ("桌面资料铺陈", "会议桌上的合同文件、签字笔和平板设备", "镜头展示资料准备完整，合同页面不可出现可读文字", "俯拍近景，文件呈斜向排布，手部从画面边缘进入", "缓慢下压"),
            ("手部翻阅合同", "商务人士手部翻阅纸质合同文件", "纸张轻微翻动，强调审阅流程", "特写，手部和文件占据画面中央，背景浅虚化", "轻微推近"),
            ("签字笔准备", "签字笔放在合同签署区域旁", "笔尖靠近纸面但还未落笔，制造签约前一刻的期待", "微距特写，浅景深，桌面纹理清晰", "静态微推"),
            ("平板方案确认", "两位商务人士查看平板上的抽象方案页面", "一人持平板，另一人用手势说明关键内容", "中近景，平板在前景中央，人物上半身清晰", "轻微横移"),
            ("文件递交", "一位商务人士把文件夹递给对方团队", "双方手部在桌面上方交接文件，动作自然克制", "中近景，手部交接位于画面中心，人物面部弱化", "缓慢推近"),
            ("合同页检查", "西装袖口和手部按住合同页边缘", "人物逐项确认合同页，桌面保持整洁", "近景，纸面占画面下半部，手部形成视觉焦点", "轻微下移"),
            ("团队资料比对", "三到五位商务人士围绕桌面资料讨论", "人物目光集中在纸质文件和平板设备上", "中景，桌面为前景，人物围成半环", "平稳横移"),
            ("会前重点标注", "商务人士用笔在文件旁做不可读标记", "只呈现动作和流程，不出现真实文字", "近景，笔尖、手部和纸张为主，背景虚化", "微距跟随"),
            ("助理整理文件", "商务助理整理多份无品牌文件夹", "文件被摆放成整齐序列，准备进入正式会谈", "中近景，桌面横向铺开，人物手部在画面上方", "轻微推入"),
            ("资料确认收束", "双方负责人在桌面前点头确认资料", "会前准备完成，画面进入正式洽谈", "中景，人物分别位于左右两侧，桌面形成稳定分界", "缓慢推近"),
        ],
    },
    {
        "group": "03_方案沟通与商务洽谈",
        "purpose": "呈现双方沟通、团队协作和方案推进",
        "preferred_categories": ["meeting", "tablet", "team", "office"],
        "beats": [
            ("会议开场讨论", "五到六位商务人士围绕会议桌讨论方案", "一位负责人站立发言，其他人认真查看资料", "中远景，站立人物在画面中部，坐席形成左右层次", "缓慢横移"),
            ("双人平板说明", "两位商务男士在窗边查看平板", "持平板者展示内容，另一人专注倾听", "中近景，平板居中，窗光形成明亮背景", "轻微推近"),
            ("团队倾听反应", "会议桌旁的团队成员专注倾听", "人物轻微点头、翻页，展现专业互动", "中景，前景肩部虚化，中景人物清晰", "轻微摇移"),
            ("方案重点手势", "商务人士用手势说明方案重点", "手势在画面中央，背景团队保持安静注视", "中近景，手部、文件和平板形成三角构图", "缓慢推入"),
            ("会议桌侧面交流", "双方代表在会议桌两侧交流", "一方说明，另一方看向文件并回应", "侧面中景，桌面横线贯穿画面", "稳定横移"),
            ("白板或屏幕前演示", "商务人士在无文字演示屏前说明合作方案", "屏幕只显示抽象图形和色块，避免可读文字", "中远景，演示者靠右，团队坐在左侧前景", "轻微推近"),
            ("文件与眼神交流", "两位负责人隔着桌面交换视线", "中间摆放合同和资料，气氛认真但积极", "中近景，桌面文件在前景，人物面部清晰", "轻微推近"),
            ("团队分组讨论", "会议室内两个小组同时低声讨论", "画面表现合作前多方协调和高效推进", "宽幅中景，前中后景都有商务人物", "缓慢横移"),
            ("会议桌俯拍秩序", "会议桌上文件、手部和平板形成协作关系", "多只手分别指向资料、拿笔或扶住文件", "俯拍中景，桌面几何线条清楚", "缓慢下压"),
            ("洽谈阶段收束", "双方负责人表情放松并交换认可动作", "沟通取得共识，为正式签约做铺垫", "中景，人物居中，窗光柔和，背景团队略虚化", "轻微推近"),
        ],
    },
    {
        "group": "04_关键条款确认",
        "purpose": "加强合同审阅、条款确认和信任建立",
        "preferred_categories": ["document", "signing", "meeting"],
        "beats": [
            ("合同条款核对", "商务人士手指按在合同关键位置", "对方代表低头查看文件，画面只呈现不可读纸面纹理", "近景，手指和文件位于画面中心", "微距推近"),
            ("并排查看文件", "两位负责人并排查看同一份合同", "人物肩部靠近，呈现共同确认的合作关系", "中近景，文件在下方前景，人物表情专注", "轻微横移"),
            ("笔记本旁合同", "合同文件、商务笔记本和签字笔整齐摆放", "镜头强调签约流程的正式和可靠", "桌面特写，物体按对角线排布", "静态微推"),
            ("法律或财务确认", "一位商务人士向团队展示文件页", "其他成员看向文件，动作克制真实", "中景，文件页在画面中央偏上", "缓慢推入"),
            ("细节确认手部", "手部轻轻敲击合同页边缘进行确认", "纸张、袖口、金属笔夹和桌面质感清晰", "微距特写，浅景深，背景完全虚化", "轻微跟随"),
            ("负责人低声沟通", "双方负责人靠近桌面低声交流", "背景团队成员安静等待，形成正式决策氛围", "中近景，人物占画面两侧，文件在中间", "缓慢横移"),
            ("资料盖章前准备", "桌面上整理好的合同和印章类办公物件", "只表现办公物件轮廓，不出现机构名称或真实章面", "近景，物件和文件形成稳定构图", "轻微推近"),
            ("确认页翻转", "合同页面被翻到签署页附近", "手部动作自然，纸张形成柔和运动模糊", "近景，纸张翻动占据前景，人物虚化", "轻微跟随"),
            ("共识眼神", "两位商务人士抬头确认对方意见", "眼神从文件转向对方，合作关系明确", "中近景，文件作为前景虚化，人物清晰", "轻微推近"),
            ("条款确认结束", "双方团队把文件整理到签署位置", "画面进入正式签约前最后准备", "中景，桌面和手部形成秩序感", "缓慢下压"),
        ],
    },
    {
        "group": "05_正式签约过程",
        "purpose": "集中呈现签署合同的核心画面，可拆分成多条高价值素材",
        "preferred_categories": ["signing", "document", "closeup"],
        "beats": [
            ("负责人落笔签署", "商务负责人用黑色签字笔在合同页签署", "笔尖落在不可读签署区域，手部动作清晰稳重", "特写，笔尖和手部居中，纸张占满下半画面", "微距推近"),
            ("双方同步签约", "两位商务人士在会议桌两侧同时签署文件", "桌面中间留出文件和笔的秩序线", "中景，左右对称构图，人物上半身自然低头", "缓慢推入"),
            ("签名页特写", "签字笔、手部和合同页局部", "只呈现书写动作，不出现可读签名或真实公司名", "微距特写，浅景深，纸张纹理清晰", "静态微推"),
            ("翻页递交签署", "一方把已签署文件递到对方面前", "对方伸手接过并准备继续签署", "中近景，文件移动形成横向动线", "轻微横移"),
            ("合同夹收拢", "签好的合同被放入深色文件夹", "文件夹、手部和西装袖口形成正式商务质感", "近景，文件夹占画面中心", "缓慢下压"),
            ("多份合同签署", "桌面上多份合同依次完成签署", "不同手部动作形成商务流程感", "俯拍中近景，多份文件斜向排列", "缓慢横移"),
            ("签约旁观反应", "团队成员在签约桌旁专注观看", "前景手部签署，背景团队略虚化", "中近景，签约动作在前景，团队形成背景层次", "轻微推近"),
            ("文件交换", "双方把签署后的合同互相交换", "手部交接动作稳定，画面简洁专业", "近景，双手与文件在画面中央", "轻微跟随"),
            ("签约完成合上文件", "负责人合上签署完成的合同文件", "动作代表签约流程完成，桌面保持干净", "近景，文件夹合拢占据画面中心", "缓慢推近"),
            ("签约段落收束", "双方负责人放下签字笔并准备起身握手", "签字笔留在文件旁，人物姿态转向对方", "中景，桌面文件前景清楚，人物上半身自然", "缓慢推入"),
        ],
    },
    {
        "group": "06_合作握手与成功达成",
        "purpose": "输出最核心的签约成功、合作握手、达成共识画面",
        "preferred_categories": ["handshake", "success", "silhouette", "applause"],
        "beats": [
            ("签约后正式握手", "两位商务负责人在会议桌旁握手", "双方团队站在身后，文件留在桌面上作为签约结果", "中景，握手动作居中，人物身体形成稳定三角", "缓慢推近"),
            ("握手手部特写", "深色西装袖口下的双手紧握", "背景会议室虚化，突出合作达成的动作瞬间", "特写，双手占画面中心，浅景深", "微距推近"),
            ("逆光剪影握手", "落地窗前两位商务人士握手形成剪影", "强逆光穿过人物轮廓，团队成员在两侧观看", "中远景，横向剪影构图，窗框线条清晰", "缓慢横移"),
            ("团队鼓掌祝贺", "会议室内商务团队鼓掌庆祝签约成功", "人物表情自然克制，避免夸张摆拍", "中景，鼓掌人物形成层次，桌面文件在前景", "轻微推近"),
            ("握手侧面镜头", "两位负责人侧身握手并微笑", "背景是明亮会议室和模糊团队成员", "中近景，握手在画面下方中心，人物面部清晰", "稳定横移"),
            ("握手低机位", "商务人士握手动作从低机位呈现", "西装袖口、桌沿和窗光增强正式质感", "低机位近景，手部和袖口形成强视觉焦点", "轻微上推"),
            ("签约文件与握手同框", "前景是签署完成的合同，背景是握手动作", "合同浅清晰，握手略虚或相反，形成成功语义", "近中景，前景文件和背景人物有明显景深", "缓慢变焦"),
            ("多人围观握手", "双方团队围绕会议桌见证负责人握手", "团队成员自然站立，画面像企业宣传片定格", "中远景，人物围成半圆，握手在中心", "缓慢推入"),
            ("窗边成功握手", "两位商务人士在明亮窗边完成握手", "窗外城市虚化，画面明亮积极", "中近景，窗光从侧后方进入，人物轮廓清楚", "轻微横移"),
            ("合作达成主视觉", "商务团队在现代会议室内完成签约后合影式站位", "两位负责人握手，双方团队在身后形成正式阵列", "宽幅中景，主体居中，空间干净完整", "缓慢推近"),
        ],
    },
    {
        "group": "07_合作落地与执行展望",
        "purpose": "从签约成功延展到合作执行、团队推进和商业未来",
        "preferred_categories": ["team", "office", "industrial", "tablet", "city"],
        "beats": [
            ("签约后方案复盘", "团队围绕桌面文件和平板继续沟通执行步骤", "气氛从正式签约转入落地推进", "中景，人物围绕桌面形成协作关系", "缓慢横移"),
            ("走廊继续交流", "双方负责人并肩走出会议室继续交流", "身后团队携带文件跟随，合作进入执行阶段", "中远景，走廊纵深构图", "稳定跟拍"),
            ("办公室执行会议", "商务团队在开放办公区讨论项目推进", "电脑、文件和玻璃隔断构成真实企业环境", "中景，前景电脑略虚化，中景人物清晰", "轻微推近"),
            ("产业现场参观", "商务人士在现代产业空间或办公展示区参观", "一人介绍空间或设备，其他人认真观察", "中远景，人物沿空间纵深排列", "缓慢横移"),
            ("平板确认执行计划", "两位商务人士在窗边查看平板执行计划", "屏幕只显示抽象色块，不出现可读文字", "中近景，平板和手势为视觉中心", "轻微推近"),
            ("文件交付给团队", "签署后的文件被交给执行团队成员", "团队成员接过文件，准备启动后续工作", "近景，文件交接动作清楚", "轻微跟随"),
            ("会议室收尾整理", "团队整理会议桌上的合同和资料", "桌面逐渐恢复整洁，流程闭环", "俯拍中景，文件和手部形成有序运动", "缓慢下压"),
            ("商务团队离场", "双方团队带着文件从会议室离开", "动作自然，空间明亮，形成段落转场", "中远景，人物从画面一侧离开", "稳定横移"),
            ("合作项目启动", "办公区内项目团队围绕显示器和资料工作", "表现签约后的执行和协作，不出现真实UI文字", "中景，显示器在右侧前景略虚，人物居中清晰", "缓慢推入"),
            ("落地执行收束", "负责人在办公室窗边回看团队工作区", "签约成功转化为实际推进的企业氛围", "中景，人物背影偏左，办公区在背景", "轻微推近"),
        ],
    },
    {
        "group": "08_品牌愿景与结尾留白",
        "purpose": "形成宣传片结尾所需的成功、远景和可放字幕留白画面",
        "preferred_categories": ["city", "silhouette", "handshake", "office", "success"],
        "beats": [
            ("高楼窗前远景收束", "商务人士站在高层窗前望向城市", "人物轮廓安静自信，表达合作后的未来展望", "中远景，人物偏右，左侧保留干净留白", "缓慢推近"),
            ("会议室空镜结尾", "签署完成后的会议桌和窗外明亮城市", "桌面文件整齐，人物离场后留下合作完成的痕迹", "宽幅中景，桌面在前景，窗景在背景", "静态微推"),
            ("剪影握手定格", "落地窗前商务握手剪影", "画面简洁有力，适合宣传片结尾或标题前背景", "远景，人物横向居中，窗光形成高反差", "缓慢横移"),
            ("团队成功背影", "商务团队并肩站在窗前形成背影", "人物看向城市，表达合作共赢和未来发展", "中远景，人物位于画面下半部，窗外留白充足", "缓慢推近"),
            ("文件与城市双重曝光感", "桌面合同文件前景和玻璃窗城市反射", "真实摄影质感，不做夸张特效", "近中景，前景文件清晰，背景城市柔和", "轻微变焦"),
            ("最后一次握手近景", "双方负责人再次握手确认合作", "画面只保留手部、袖口和柔和背景", "特写，手部居中，浅景深", "微距推近"),
            ("商务楼宇夜景", "现代办公楼灯光与城市夜色", "结尾提供企业宣传片可用的安静背景", "远景，建筑居中，天空和玻璃反射保留留白", "缓慢上升"),
            ("会议室团队剪影", "会议室内团队成员在窗边交流的剪影", "人物动作轻微，空间保持专业安静", "中远景，人物偏下，窗框线条明确", "缓慢横移"),
            ("合作共赢收束画面", "商务团队站在现代会议室中形成成功合影式关系", "不出现真实品牌和文字，画面干净高级", "宽幅中景，主体居中，左右空间平衡", "缓慢推近"),
            ("结尾留白主视觉", "明亮现代商务空间中的合作成功氛围", "前景可为签约文件或桌面，背景是高层窗光和商务人物轮廓", "宽幅中远景，右侧人物，左侧大面积干净留白", "静态微推"),
        ],
    },
]


def export_jiaozi_storyboard_script(
    project_dir: str | Path,
    shot_count: int = 80,
    output_json: str | Path | None = None,
    duration_per_shot: int = DEFAULT_SHOT_DURATION,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    if not project_path.exists():
        return {
            "system_output_success": False,
            "system_output_project_dir": str(project_path),
            "system_output_storyboard_script_json": "",
            "system_output_message": "项目目录不存在，无法生成 JiaoziStudio 分镜脚本。",
        }

    payload = build_jiaozi_storyboard_payload(
        project_path,
        shot_count=shot_count,
        duration_per_shot=duration_per_shot,
    )
    export_dir = ensure_dir(project_path / EXPORT_DIR_NAME)
    script_path = Path(output_json) if output_json else export_dir / "JiaoziStudio专用80镜头脚本.json"
    if script_path.suffix.lower() != ".json":
        script_path = script_path.with_suffix(".json")
    audit_payload = audit_jiaozi_storyboard_payload(payload, auto_fix=True)
    payload = audit_payload["payload"]
    payload.setdefault("skillMetadata", {})["reference_audit_summary"] = audit_payload["summary"]
    write_json(script_path, payload)
    markdown_path = write_text(export_dir / "80镜头画面分镜脚本.md", build_storyboard_markdown(payload))
    audit_report_path = write_json(export_dir / "JiaoziStudio逐镜头参考审校报告.json", audit_payload["report"])
    audit_markdown_path = write_text(export_dir / "JiaoziStudio逐镜头参考审校报告.md", build_storyboard_audit_markdown(audit_payload["report"]))

    return {
        "system_output_success": True,
        "system_output_project_dir": str(project_path),
        "system_output_storyboard_script_json": str(script_path),
        "system_output_storyboard_script_markdown": str(markdown_path),
        "system_output_reference_audit_json": str(audit_report_path),
        "system_output_reference_audit_markdown": str(audit_markdown_path),
        "system_output_reference_audit_issue_count": audit_payload["summary"]["issue_count"],
        "system_output_reference_audit_fixed_count": audit_payload["summary"]["fixed_count"],
        "system_output_shot_count": payload["shotCount"],
        "system_output_reference_asset_count": len(payload.get("referenceAssets", [])),
        "system_output_message": "已生成包含本地参考图地址的 JiaoziStudio 80 镜头分镜脚本。",
    }


def audit_jiaozi_storyboard_script(
    project_dir: str | Path,
    script_json: str | Path | None = None,
    auto_fix: bool = False,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    export_dir = ensure_dir(project_path / EXPORT_DIR_NAME)
    script_path = Path(script_json) if script_json else export_dir / "JiaoziStudio专用80镜头脚本.json"
    if not script_path.exists():
        return {
            "system_output_success": False,
            "system_output_project_dir": str(project_path),
            "system_output_storyboard_script_json": str(script_path),
            "system_output_message": "未找到 JiaoziStudio 分镜脚本 JSON，无法审校。",
        }
    payload = read_json(script_path)
    audit_payload = audit_jiaozi_storyboard_payload(payload, auto_fix=auto_fix)
    payload = audit_payload["payload"]
    payload.setdefault("skillMetadata", {})["reference_audit_summary"] = audit_payload["summary"]
    report_path = write_json(export_dir / "JiaoziStudio逐镜头参考审校报告.json", audit_payload["report"])
    markdown_path = write_text(export_dir / "JiaoziStudio逐镜头参考审校报告.md", build_storyboard_audit_markdown(audit_payload["report"]))
    if auto_fix or not audit_payload["summary"]["issue_count"]:
        write_json(script_path, payload)
        write_text(export_dir / "80镜头画面分镜脚本.md", build_storyboard_markdown(payload))
    return {
        "system_output_success": True,
        "system_output_project_dir": str(project_path),
        "system_output_storyboard_script_json": str(script_path),
        "system_output_reference_audit_json": str(report_path),
        "system_output_reference_audit_markdown": str(markdown_path),
        "system_output_reference_audit_issue_count": audit_payload["summary"]["issue_count"],
        "system_output_reference_audit_blocking_count": audit_payload["summary"]["blocking_count"],
        "system_output_reference_audit_fixed_count": audit_payload["summary"]["fixed_count"],
        "system_output_message": "已逐镜头审校参考图、图片提示词和视频提示词；auto-fix 开启时已自动解绑明显冲突参考图。",
    }


def audit_jiaozi_storyboard_payload(payload: Dict[str, Any], auto_fix: bool = False) -> Dict[str, Any]:
    reference_assets = payload.get("referenceAssets", []) or []
    asset_by_frame_id = {
        str((asset.get("metadata") or {}).get("frame_id") or ""): asset
        for asset in reference_assets
        if (asset.get("metadata") or {}).get("frame_id")
    }
    prompt_by_shot_id = {
        str(item.get("shot_id") or ""): item
        for item in payload.get("prompts", []) or []
        if item.get("shot_id")
    }
    detailed = payload.get("detailed_script", {}) or {}
    detailed_shots = detailed.get("shots", []) if isinstance(detailed, dict) else []
    detailed_by_shot_id = {
        str(item.get("shot_id") or ""): item
        for item in detailed_shots
        if item.get("shot_id")
    }
    shot_by_id = {
        str(shot.get("shot_id") or ""): shot
        for shot in payload.get("storyboard_master", []) or []
        if shot.get("shot_id")
    }
    plan_items = (payload.get("reference_image_plan") or {}).get("items", []) or []
    plan_by_shot_id = {
        str(item.get("shot_id") or ""): item
        for item in plan_items
        if item.get("shot_id")
    }
    report_items: List[Dict[str, Any]] = []
    issue_count = 0
    blocking_count = 0
    fixed_count = 0
    global_style = str(payload.get("globalStyle") or payload.get("stylePrompt") or "")
    negative_prompt = str(payload.get("negativePrompt") or "")

    for shot in payload.get("storyboard_master", []) or []:
        shot_id = str(shot.get("shot_id") or "")
        spec = _spec_from_storyboard_shot(shot)
        issues = _audit_storyboard_shot(shot, spec, asset_by_frame_id)
        issues.extend(_audit_derived_anchor_consistency(shot, spec, shot_by_id))
        issue_count += len(issues)
        blocking_count += len([issue for issue in issues if issue.get("severity") == "block"])
        applied_fixes: List[str] = []
        if auto_fix and issues:
            if any(issue.get("type") in {"reference_conflict", "reference_missing", "prompt_reference_stale", "derived_scene_conflict"} and issue.get("severity") == "block" for issue in issues):
                _unbind_storyboard_reference(
                    payload,
                    shot,
                    spec,
                    global_style,
                    negative_prompt,
                    prompt_by_shot_id.get(shot_id),
                    detailed_by_shot_id.get(shot_id),
                    plan_by_shot_id.get(shot_id),
                )
                applied_fixes.append("已解绑冲突参考图，并重写为原创规划参考说明")
            if any(issue.get("type") == "video_motion_conflict" and issue.get("severity") == "block" for issue in issues):
                video_prompt = _compose_video_prompt(spec, None)
                shot["videoPrompt"] = video_prompt
                shot["video_prompt"] = video_prompt
                if prompt_by_shot_id.get(shot_id):
                    prompt_by_shot_id[shot_id]["video_prompt"] = video_prompt
                if detailed_by_shot_id.get(shot_id):
                    detailed_by_shot_id[shot_id]["video_prompt"] = video_prompt
                applied_fixes.append("已按当前镜头主体和动作重写视频提示词")
            if applied_fixes:
                fixed_count += 1
        report_items.append(
            {
                "shot_id": shot_id,
                "shot_title": shot.get("shot_title") or shot.get("title") or "",
                "scene_group": shot.get("scene_group") or "",
                "reference_frame_ids": shot.get("reference_frame_ids") or [],
                "reference_image_paths": shot.get("reference_frame_paths") or [],
                "status": "needs_review" if issues and not applied_fixes else ("fixed" if applied_fixes else "ok"),
                "issues": issues,
                "applied_fixes": applied_fixes,
                "codex_visual_review_instruction": _codex_visual_review_instruction(shot, issues),
            }
        )

    used_frame_ids = sorted({
        frame_id
        for item in (payload.get("reference_image_plan") or {}).get("items", []) or []
        for frame_id in item.get("reference_frame_ids", []) or []
    })
    summary = {
        "shot_count": len(payload.get("storyboard_master", []) or []),
        "reference_asset_count": len(reference_assets),
        "used_reference_frame_count": len(used_frame_ids),
        "unbound_original_shot_count": len([
            item for item in (payload.get("reference_image_plan") or {}).get("items", []) or []
            if not item.get("reference_frame_ids")
        ]),
        "issue_count": issue_count,
        "blocking_count": blocking_count,
        "fixed_count": fixed_count,
        "auto_fix": bool(auto_fix),
    }
    report = {
        "schema_version": "jiaozi-storyboard-reference-audit/v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "review_policy": (
            "逐镜头检查镜头主体/动作、绑定参考图视觉分析、图片提示词参考说明和视频动态是否一致；"
            "明显冲突时优先解绑参考图，保持当前镜头原创规划，不强行复刻参考帧。"
        ),
        "items": report_items,
    }
    return {"payload": payload, "report": report, "summary": summary}


def _spec_from_storyboard_shot(shot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": shot.get("shot_title") or shot.get("title") or "",
        "group": shot.get("scene_group") or "",
        "purpose": shot.get("scene_goal") or "",
        "subject": shot.get("subject_main") or shot.get("subject") or "",
        "secondary": shot.get("subject_secondary") or [],
        "action": shot.get("action_description") or "",
        "scene": shot.get("scene_context") or "",
        "shot_type": shot.get("shot_size") or "",
        "camera_angle": shot.get("camera_angle") or "",
        "motion": shot.get("camera_movement") or "",
        "composition": shot.get("composition_notes") or shot.get("direct_use_composition") or "",
        "lighting": shot.get("lighting_style") or "",
        "color": shot.get("color_palette") or "",
        "mood": shot.get("mood_tone") or "",
        "shot_role": shot.get("shot_role") or _storyboard_role_from_group(str(shot.get("scene_group") or "")),
    }


def _storyboard_role_from_group(group: str) -> str:
    if "开场" in group:
        return "establishing"
    if "主体" in group:
        return "main_subject"
    if "过程" in group or "签约" in group or "动作" in group:
        return "process_action"
    if "细节" in group or "特写" in group or "条款" in group:
        return "detail_closeup"
    if "人物" in group or "使用" in group or "洽谈" in group or "会议" in group:
        return "people_usage"
    if "转场" in group:
        return "transition_mood"
    if "成果" in group or "情绪" in group or "握手" in group or "达成" in group:
        return "outcome_emotion"
    if "结尾" in group or "留白" in group:
        return "end_copy_space"
    return "main_subject"


def _audit_storyboard_shot(
    shot: Dict[str, Any],
    spec: Dict[str, Any],
    asset_by_frame_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    shot_text = _search_text([
        shot.get("shot_title"),
        shot.get("subject_main"),
        shot.get("action_description"),
        shot.get("scene_context"),
        shot.get("imagePrompt"),
    ])
    image_prompt = str(shot.get("imagePrompt") or "")
    frame_ids = [str(frame_id) for frame_id in shot.get("reference_frame_ids", []) or [] if str(frame_id)]
    if not frame_ids:
        if "参考这张图" in image_prompt:
            issues.append(_audit_issue("prompt_reference_stale", "block", "镜头没有绑定参考图，但图片提示词仍写着参考这张图。"))
        issues.extend(_video_motion_conflict_issues(shot, spec))
        return issues

    for frame_id in frame_ids:
        asset = asset_by_frame_id.get(frame_id)
        metadata = dict((asset or {}).get("metadata") or {})
        if not asset:
            issues.append(_audit_issue("reference_missing", "block", f"绑定的参考帧 {frame_id} 不在 referenceAssets 中。"))
            continue
        source_path = str(asset.get("sourcePath") or "")
        if source_path and not Path(source_path).exists():
            issues.append(_audit_issue("reference_file_missing", "warn", f"参考图本地文件不存在：{source_path}"))
        if _reference_semantic_conflict(metadata, spec):
            issues.append(
                _audit_issue(
                    "reference_conflict",
                    "block",
                    f"参考图语义与镜头不匹配：镜头是“{spec.get('subject')}”，参考图说明是“{metadata.get('prompt_ready_brief') or metadata.get('visual_summary') or frame_id}”。",
                    source_path,
                )
            )
            continue
        role_issue = _reference_role_conflict_reason(metadata, spec, shot_text)
        if role_issue:
            issues.append(_audit_issue("reference_conflict", "block", role_issue, source_path))
        if "参考这张图" not in image_prompt:
            issues.append(_audit_issue("prompt_reference_missing", "warn", "镜头绑定了参考图，但图片提示词没有说明参考图要参考什么。", source_path))

    issues.extend(_video_motion_conflict_issues(shot, spec))
    return issues


def _reference_role_conflict_reason(frame: Dict[str, Any], spec: Dict[str, Any], shot_text: str) -> str:
    tags = set(_as_list(frame.get("shot_role_tags"))) | set(_as_list(frame.get("composition_tags")))
    frame_text = _search_text([
        frame.get("visual_summary"),
        frame.get("prompt_ready_brief"),
        frame.get("subject_type"),
        frame.get("scene_type"),
    ])
    role = _spec_primary_role(spec)
    if role == "establishing" and tags & {"detail_closeup", "closeup", "macro"} and not tags & {"establishing", "wide", "copy_space", "depth"}:
        return "建立/空间镜头绑定了局部特写参考图，容易导致主体和景别冲突。"
    if role == "detail_closeup" and tags & {"establishing", "wide"} and not tags & {"detail_closeup", "closeup", "macro"}:
        return "细节特写镜头绑定了空间/远景参考图，无法服务局部材质或动作细节。"
    if re.search(r"握手", shot_text) and not re.search(r"握手|交握|双手紧握", frame_text):
        return "握手镜头绑定的参考图没有明确握手关系。"
    if re.search(r"鼓掌|祝贺|认可", shot_text) and not re.search(r"鼓掌|祝贺|认可", frame_text):
        return "鼓掌/认可镜头绑定的参考图没有明确鼓掌或认可动作。"
    signing_focus = bool(re.search(r"签字(?!笔)|签署|落笔|笔尖", shot_text))
    pen_detail_focus = role in {"detail_closeup", "process_action"} and bool(re.search(r"签字笔|钢笔|笔尖", shot_text))
    if (signing_focus or pen_detail_focus) and not re.search(r"签字|签署|笔尖|钢笔|合同纸面|纸面|签字笔", frame_text):
        return "签字/签署镜头绑定的参考图没有明确签字、笔尖或纸面关系。"
    return ""


def _video_motion_conflict_issues(shot: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    subject = _search_text([
        shot.get("shot_title"),
        shot.get("subject_main"),
        shot.get("action_description"),
        shot.get("scene_context"),
    ])
    video = _search_text([re.split(r"不要出现\s*[：:]", str(shot.get("videoPrompt") or shot.get("video_prompt") or ""), maxsplit=1)[0]])
    issues: List[Dict[str, Any]] = []
    if re.search(r"鼓掌|祝贺|认可", subject) and re.search(r"握手|签字笔|笔尖|纸面滑过", video):
        issues.append(_audit_issue("video_motion_conflict", "block", "视频提示词动作与鼓掌/认可镜头不一致。"))
    if re.search(r"握手", subject) and re.search(r"鼓掌|签字笔|笔尖|纸面滑过", video):
        issues.append(_audit_issue("video_motion_conflict", "block", "视频提示词动作与握手镜头不一致。"))
    if re.search(r"签字|签署|笔尖", subject) and not re.search(r"握手|鼓掌|祝贺|认可", subject) and re.search(r"握手|鼓掌", video):
        issues.append(_audit_issue("video_motion_conflict", "block", "视频提示词动作与签字/签署镜头不一致。"))
    positive_video = re.sub(r"无人物进入|不出现人物|不要出现人物|没有人物|无人物", "", video)
    if re.search(NEV_STORY_PATTERN, subject) and re.search(BUSINESS_MOTION_PATTERN, positive_video):
        issues.append(_audit_issue("video_motion_conflict", "block", "新能源车辆镜头的视频提示词混入了商务会议、文件或人物入场动作。"))
    if re.search(r"自动驾驶|智能驾驶|智驾|车道|前车|巡航|HUD|道路", subject) and re.search(r"会议室|会议区域|商务人士|手持文件|合同|桌面资料|桌面道具", positive_video):
        issues.append(_audit_issue("video_motion_conflict", "block", "道路智驾镜头的视频提示词混入了室内商务空间。"))
    if re.search(r"空会议室|空会议桌|空镜|桌面准备", subject) and re.search(r"人物进入|商务人士进入|商务人士.*走|握手|鼓掌", positive_video):
        issues.append(_audit_issue("video_motion_conflict", "block", "视频提示词给空镜加入了人物或动作。"))
    if re.search(r"楼宇|建筑|幕墙|天际线|外景", subject) and re.search(r"握手|签字|鼓掌|会议桌旁|合同", video):
        issues.append(_audit_issue("video_motion_conflict", "block", "视频提示词给建筑外景加入了室内商务动作。"))
    return issues


def _audit_derived_anchor_consistency(
    shot: Dict[str, Any],
    spec: Dict[str, Any],
    shot_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    dependency = shot.get("reference_dependency") or {}
    role = str(dependency.get("role") or shot.get("reference_role") or "")
    if role != "derived_view":
        return []
    anchor_id = str(dependency.get("anchor_shot_id") or shot.get("reference_shot_id") or "")
    if not anchor_id:
        return [_audit_issue("derived_scene_conflict", "block", "派生镜头缺少 reference_shot_id，无法确定锚点图。")]
    anchor = shot_by_id.get(anchor_id)
    if not anchor:
        return [_audit_issue("derived_scene_conflict", "block", f"派生镜头指向的锚点 {anchor_id} 不存在。")]
    anchor_family = _spec_scene_family(_spec_from_storyboard_shot(anchor))
    derived_family = _spec_scene_family(spec)
    if anchor_family != derived_family:
        return [
            _audit_issue(
                "derived_scene_conflict",
                "block",
                f"派生镜头场景族与锚点不一致：derived={derived_family}，anchor={anchor_family}。派生图会导致场景/人物/气氛不连贯。",
            )
        ]
    return []


def _audit_issue(issue_type: str, severity: str, message: str, reference_image_path: str = "") -> Dict[str, Any]:
    return {
        "type": issue_type,
        "severity": severity,
        "message": message,
        "reference_image_path": reference_image_path,
    }


def _unbind_storyboard_reference(
    payload: Dict[str, Any],
    shot: Dict[str, Any],
    spec: Dict[str, Any],
    global_style: str,
    negative_prompt: str,
    prompt_item: Dict[str, Any] | None,
    detailed_item: Dict[str, Any] | None,
    plan_item: Dict[str, Any] | None,
) -> None:
    storyboard_lane = str(shot.get("storyboard_lane") or "main")
    image_prompt = _compose_image_prompt(spec, None, global_style, negative_prompt, storyboard_lane)
    negative = _compose_negative_prompt(None, negative_prompt)
    reference_usage = _reference_usage_text(None)
    dependency = dict(shot.get("reference_dependency") or {})
    dependency.update(
        {
            "role": "standalone",
            "anchor_shot_id": None,
            "reference_image_path": None,
            "market_reference_asset_ids": [],
            "market_reference_asset_paths": [],
            "reference_reason": reference_usage,
            "market_reference_usage": reference_usage,
            "reference_frame_ids": [],
            "reference_frame_paths": [],
            "local_reference_file_url": "",
            "reference_reuse_budget": 0,
            "reference_reuse_reason": "",
            "reference_usage_role": "original_planning",
            "reference_reuse_group": "",
        }
    )
    shot["imagePrompt"] = image_prompt
    shot["image_prompt"] = image_prompt
    shot["negativePrompt"] = negative
    shot["negative_constraints"] = negative
    shot["reference_dependency"] = dependency
    shot["reference_frame_ids"] = []
    shot["reference_frame_paths"] = []
    shot["reference_frame_usage_notes"] = reference_usage
    if prompt_item is not None:
        prompt_item["prompt"] = image_prompt
        prompt_item["negative_prompt"] = negative
        prompt_item["reference_image_plan"] = {
            "role": "standalone",
            "reference_shot_id": None,
            "reference_image_path": None,
            "market_reference_asset_ids": [],
            "market_reference_asset_paths": [],
            "reference_usage_role": "original_planning",
            "reference_reuse_group": "",
            "reference_reuse_budget": 0,
            "storyboard_lane": storyboard_lane,
        }
    if detailed_item is not None:
        detailed_item["image_prompt"] = image_prompt
        detailed_item["negative_prompt"] = negative
        detailed_item["reference_asset_ids"] = []
        detailed_item["reference_frame_ids"] = []
        detailed_item["reference_image_paths"] = []
        detailed_item["reference_file_urls"] = []
        detailed_item["reference_usage"] = reference_usage
    if plan_item is not None:
        plan_item.update(
            {
                "reference_role": "standalone",
                "reference_shot_id": None,
                "reference_image_path": None,
                "reference_reason": reference_usage,
                "market_reference_asset_ids": [],
                "market_reference_asset_paths": [],
                "market_reference_usage": reference_usage,
                "reference_frame_ids": [],
                "reference_frame_paths": [],
                "reference_usage_role": "original_planning",
                "reference_reuse_group": "",
                "reference_reuse_budget": 0,
                "reference_reuse_reason": "",
            }
        )


def _codex_visual_review_instruction(shot: Dict[str, Any], issues: Sequence[Dict[str, Any]]) -> str:
    if not issues:
        return "无需人工复核；本条镜头的参考图、图片提示词和视频提示词通过自动审校。"
    paths = [issue.get("reference_image_path") for issue in issues if issue.get("reference_image_path")]
    path_text = "；".join(paths) if paths else "无绑定参考图或参考图路径缺失"
    return (
        f"请 Codex 打开参考图路径：{path_text}，对照镜头“{shot.get('shot_title') or shot.get('shot_id')}”的"
        "主体、场景、动作、构图、光线和视频动态逐项复核；如果参考图不能服务当前画面，应保持解绑或重新选择更匹配参考图。"
    )


def build_storyboard_audit_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# JiaoziStudio 逐镜头参考审校报告",
        "",
        f"- 镜头数：{summary.get('shot_count', 0)}",
        f"- 参考素材数：{summary.get('reference_asset_count', 0)}",
        f"- 问题数：{summary.get('issue_count', 0)}",
        f"- 阻断问题：{summary.get('blocking_count', 0)}",
        f"- 自动修正：{summary.get('fixed_count', 0)}",
        "",
    ]
    for item in report.get("items", []) or []:
        if item.get("status") == "ok":
            continue
        lines.extend(
            [
                f"## {item.get('shot_id')} {item.get('shot_title')}",
                f"- 分组：{item.get('scene_group', '')}",
                f"- 状态：{item.get('status')}",
                f"- 参考帧：{', '.join(item.get('reference_frame_ids') or []) or '无'}",
            ]
        )
        for issue in item.get("issues", []) or []:
            lines.append(f"- [{issue.get('severity')}] {issue.get('type')}：{issue.get('message')}")
            if issue.get("reference_image_path"):
                lines.append(f"  - 参考图：{issue.get('reference_image_path')}")
        for fix in item.get("applied_fixes", []) or []:
            lines.append(f"- 自动修正：{fix}")
        lines.append(f"- Codex 视觉复核：{item.get('codex_visual_review_instruction', '')}")
        lines.append("")
    if len(lines) <= 10:
        lines.append("所有镜头均通过自动审校。")
    return "\n".join(lines).strip() + "\n"


def build_jiaozi_storyboard_payload(
    project_dir: str | Path,
    shot_count: int = 80,
    duration_per_shot: int = DEFAULT_SHOT_DURATION,
) -> Dict[str, Any]:
    project_path = Path(project_dir)
    selected_frames = load_selected_reference_frames(project_path)
    if not selected_frames:
        raise ValueError("未找到精选参考帧，请先完成筛选并生成 00_调研/精选参考帧/精选参考帧清单.json。")

    topic = _resolve_topic(project_path)
    market_context = _load_market_context(project_path)
    frame_assets = _build_reference_assets(selected_frames, project_path)
    topic_profile = _build_topic_profile(topic, market_context, selected_frames)
    shot_specs = _build_shot_specs(max(1, int(shot_count or 80)), topic_profile, selected_frames)
    assignments = _assign_frames_to_specs(selected_frames, shot_specs)

    global_style = _build_global_style(topic_profile)
    negative_prompt = _build_negative_prompt(topic_profile, selected_frames)

    storyboard_master: List[Dict[str, Any]] = []
    detailed_script: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []
    reference_plan_items: List[Dict[str, Any]] = []
    frame_usage_seen: Dict[str, int] = {}
    assignment_counts: Dict[str, int] = {}
    for frame in assignments:
        if frame:
            frame_id = str(frame.get("frame_id") or "")
            if frame_id:
                assignment_counts[frame_id] = assignment_counts.get(frame_id, 0) + 1
    anchor_shot_by_frame: Dict[str, str] = {}

    for index, spec in enumerate(shot_specs, start=1):
        frame = assignments[index - 1]
        asset = frame_assets[frame["frame_id"]] if frame else None
        frame_id = str(frame.get("frame_id") or "") if frame else ""
        frame_usage_index = frame_usage_seen.get(frame_id, 0) if frame_id else 0
        storyboard_lane = _storyboard_lane_for_assignment(frame, frame_usage_index)
        storyboard_lane_label = "高价值参考延展" if storyboard_lane == "extension" else "主线素材"
        shot_id = f"shot_{index:03d}"
        group = spec["group"]
        has_multiview_chain = bool(frame_id and assignment_counts.get(frame_id, 0) > 1)
        role = "anchor" if has_multiview_chain and frame_usage_index == 0 else ("derived_view" if has_multiview_chain else "standalone")
        anchor_id = anchor_shot_by_frame.get(frame_id) if role == "derived_view" else None
        direct_asset = asset if role != "derived_view" else None
        image_prompt = _compose_image_prompt(
            spec,
            frame,
            global_style,
            negative_prompt,
            storyboard_lane,
            reference_role=role,
            anchor_shot_id=anchor_id,
        )
        video_prompt = _compose_video_prompt(spec, frame)
        negative = _compose_negative_prompt(frame, negative_prompt)
        reference_usage = _reference_usage_text(frame) if role != "derived_view" else _anchor_reference_usage_text(anchor_id, frame)
        reference_reuse_budget = _reference_reuse_budget(frame) if frame else 0
        reference_usage_role = _reference_usage_role(frame) if frame and role != "derived_view" else ("anchor_derived" if role == "derived_view" else "original_planning")
        reference_reuse_group = _reference_reuse_group(spec, frame) if frame else ""
        dependency = {
            "role": role,
            "anchor_shot_id": anchor_id,
            "reference_image_path": direct_asset["sourcePath"] if direct_asset else None,
            "market_reference_asset_ids": [direct_asset["id"]] if direct_asset else [],
            "market_reference_asset_paths": [direct_asset["sourcePath"]] if direct_asset else [],
            "reference_reason": reference_usage,
            "market_reference_usage": reference_usage,
            "reference_frame_ids": [frame["frame_id"]] if frame and role != "derived_view" else [],
            "reference_frame_paths": [direct_asset["sourcePath"]] if direct_asset else [],
            "inherited_reference_frame_ids": [frame["frame_id"]] if frame and role == "derived_view" else [],
            "inherited_reference_frame_paths": [asset["sourcePath"]] if asset and role == "derived_view" else [],
            "local_reference_file_url": direct_asset["url"] if direct_asset else "",
            "reference_reuse_budget": reference_reuse_budget,
            "reference_reuse_reason": _reference_reuse_reason(frame, reference_reuse_budget) if frame else "",
            "reference_usage_role": reference_usage_role,
            "reference_reuse_group": reference_reuse_group,
            "storyboard_lane": storyboard_lane,
            "storyboard_lane_label": storyboard_lane_label,
        }
        shot = {
            "shot_id": shot_id,
            "shot_title": spec["title"],
            "duration": duration_per_shot,
            "storyboard_lane": storyboard_lane,
            "storyboard_lane_label": storyboard_lane_label,
            "scene_group": group,
            "shot_role": spec.get("shot_role"),
            "scene_goal": spec["purpose"],
            "subject_main": spec["subject"],
            "subject_secondary": spec.get("secondary", []),
            "action_description": spec["action"],
            "scene_context": spec["scene"],
            "shot_size": spec["shot_type"],
            "camera_angle": spec["camera_angle"],
            "camera_movement": spec["motion"],
            "composition_notes": spec["composition"],
            "direct_use_composition": spec["composition"],
            "lighting_style": spec["lighting"],
            "mood_tone": spec["mood"],
            "color_palette": spec["color"],
            "visual_style": global_style,
            "imagePrompt": image_prompt,
            "videoPrompt": video_prompt,
            "negativePrompt": negative,
            "image_prompt": image_prompt,
            "video_prompt": video_prompt,
            "negative_constraints": negative,
            "reference_dependency": dependency,
            "reference_frame_ids": [frame["frame_id"]] if frame and role != "derived_view" else [],
            "reference_frame_paths": [direct_asset["sourcePath"]] if direct_asset else [],
            "inherited_reference_frame_ids": [frame["frame_id"]] if frame and role == "derived_view" else [],
            "inherited_reference_frame_paths": [asset["sourcePath"]] if asset and role == "derived_view" else [],
            "reference_frame_usage_notes": reference_usage,
            "generate_status": "draft",
            "sourceFormat": "ai_video_asset_skill_v1",
        }
        storyboard_master.append(shot)
        detailed_script.append(
            {
                "shot_id": shot_id,
                "title": spec["title"],
                "duration": duration_per_shot,
                "scene_group": group,
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
                "negative_prompt": negative,
                "reference_asset_ids": [direct_asset["id"]] if direct_asset else [],
                "reference_frame_ids": [frame["frame_id"]] if frame and role != "derived_view" else [],
                "reference_image_paths": [direct_asset["sourcePath"]] if direct_asset else [],
                "reference_file_urls": [direct_asset["url"]] if direct_asset else [],
                "reference_role": role,
                "reference_shot_id": anchor_id,
                "inherited_reference_frame_ids": [frame["frame_id"]] if frame and role == "derived_view" else [],
                "reference_usage": reference_usage,
                "storyboard_lane": storyboard_lane,
                "storyboard_lane_label": storyboard_lane_label,
            }
        )
        prompts.append(
            {
                "shot_id": shot_id,
                "provider": "codex_image2",
                "prompt": image_prompt,
                "negative_prompt": negative,
                "aspect_ratio": DEFAULT_ASPECT_RATIO,
                "reference_image_plan": {
                    "role": role,
                    "reference_shot_id": anchor_id,
                    "reference_image_path": direct_asset["sourcePath"] if direct_asset else None,
                    "market_reference_asset_ids": [direct_asset["id"]] if direct_asset else [],
                    "market_reference_asset_paths": [direct_asset["sourcePath"]] if direct_asset else [],
                    "reference_usage_role": reference_usage_role,
                    "reference_reuse_group": reference_reuse_group,
                    "reference_reuse_budget": reference_reuse_budget,
                    "inherited_reference_frame_ids": [frame["frame_id"]] if frame and role == "derived_view" else [],
                    "storyboard_lane": storyboard_lane,
                },
            }
        )
        reference_plan_items.append(
            {
                "shot_id": shot_id,
                "scene_group": group,
                "reference_role": role,
                "reference_shot_id": anchor_id,
                "reference_image_path": direct_asset["sourcePath"] if direct_asset else None,
                "planned_current_image_path": f"03_图片/镜头_{index:03d}/当前图.png",
                "reference_reason": reference_usage,
                "market_reference_asset_ids": [direct_asset["id"]] if direct_asset else [],
                "market_reference_asset_paths": [direct_asset["sourcePath"]] if direct_asset else [],
                "market_reference_usage": reference_usage,
                "reference_frame_ids": [frame["frame_id"]] if frame and role != "derived_view" else [],
                "reference_frame_paths": [direct_asset["sourcePath"]] if direct_asset else [],
                "inherited_reference_frame_ids": [frame["frame_id"]] if frame and role == "derived_view" else [],
                "inherited_reference_frame_paths": [asset["sourcePath"]] if asset and role == "derived_view" else [],
                "reference_usage_role": reference_usage_role,
                "reference_reuse_group": reference_reuse_group,
                "reference_reuse_budget": reference_reuse_budget,
                "reference_reuse_reason": _reference_reuse_reason(frame, reference_reuse_budget) if frame else "",
                "storyboard_lane": storyboard_lane,
                "storyboard_lane_label": storyboard_lane_label,
            }
        )
        if role == "anchor" and frame_id:
            anchor_shot_by_frame[frame_id] = shot_id
        if frame_id:
            frame_usage_seen[frame_id] = frame_usage_index + 1

    reference_assets = list(frame_assets.values())
    used_frame_ids = sorted({
        frame_id
        for item in reference_plan_items
        for frame_id in [*item.get("reference_frame_ids", []), *item.get("inherited_reference_frame_ids", [])]
    })
    payload = {
        "format": "ai_video_asset_storyboard_script_v1",
        "schema_version": "jiaozi-storyboard-plan/v1",
        "topic": topic,
        "project_title": topic,
        "materialGoal": f"生成 {len(storyboard_master)} 个围绕“{topic}”的商业 AI 视频素材镜头，覆盖开场、主体展示、过程动作、细节、使用场景、转场、成果和结尾留白，导入 JiaoziStudio 后可拆成图片节点。",
        "globalStyle": global_style,
        "stylePrompt": global_style,
        "negativePrompt": negative_prompt,
        "aspectRatio": DEFAULT_ASPECT_RATIO,
        "resolution": DEFAULT_RESOLUTION,
        "totalDuration": len(storyboard_master) * duration_per_shot,
        "shotCount": len(storyboard_master),
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
        "sourceFormat": "ai_video_asset_skill_v1",
        "skillProjectDir": str(project_path.resolve()),
        "skillProjectName": project_path.name,
        "referenceStrategy": (
            "全部精选参考帧都写入 referenceAssets；镜头只绑定用途匹配的本地参考帧，"
            "高价值参考帧先生成锚点图，再由锚点图延展 1-2 个同场景多机位镜头；"
            "没有明确匹配关系的镜头保持原创规划，不强行连接参考图；"
            "低相关或高风险帧保留为证据素材不强行进入 image2 参考；referenceAssets.url 使用 file:// 地址，sourcePath 保留 Windows 原图路径。"
        ),
        "referenceAssets": reference_assets,
        "reference_image_plan": {
            "strategy": "按商业素材包功能分组排序；精选参考帧只绑定到用途匹配的镜头。高价值参考帧第一次生成 anchor 锚点图，后续 1-2 个同语义镜头作为 derived_view 参考锚点图，保持同一场景/人物/光线连续性。",
            "items": reference_plan_items,
        },
        "storyboard_master": storyboard_master,
        "detailed_script": {"topic": topic, "shots": detailed_script},
        "prompts": prompts,
        "project_manifest": _read_json_default(project_path / "项目清单.json", _read_json_default(project_path / "project_manifest.json", {})),
        "skillMetadata": {
            "generated_by": "ai-video-asset-skill",
            "market_context": market_context,
            "selected_reference_frame_count": len(selected_frames),
            "used_reference_frame_count": len(used_frame_ids),
            "unbound_original_shot_count": len([item for item in reference_plan_items if not item.get("reference_frame_ids")]),
            "all_selected_reference_frames_preserved": len(reference_assets) == len(selected_frames),
            "all_selected_reference_frames_used": len(used_frame_ids) == len(selected_frames),
            "reference_binding_policy": "reference_pool_anchor_then_derived_optional_binding",
            "reference_reuse_policy": "每张精选参考帧按画面价值动态计算 0-3 次复用预算；复用超过 1 次时第一条为 anchor，后续为 derived_view，并直接参考锚点生成图而不是继续直接参考上传原图。",
            "derived_view_count": len([item for item in reference_plan_items if item.get("reference_role") == "derived_view"]),
            "anchor_count": len([item for item in reference_plan_items if item.get("reference_role") == "anchor"]),
            "topic_profile": topic_profile,
            "diversity_report": _build_diversity_report(storyboard_master, reference_plan_items),
            "local_path_policy": "脚本保留 sourcePath/file url；普通浏览器无法直接读取任意磁盘路径，JiaoziStudio 导入后会保留地址供本地/Electron 桥接或人工上传。",
        },
    }
    return payload


def load_selected_reference_frames(project_path: Path) -> List[Dict[str, Any]]:
    selected_dir = project_path / RESEARCH_DIR_NAME / SELECTED_REFERENCE_DIR_NAME
    selected_payload = _read_json_default(selected_dir / "精选参考帧清单.json", {"frames": []})
    analysis_payload = _read_json_default(selected_dir / "参考帧分析.json", {"frames": []})
    analysis_by_id = {
        str(item.get("frame_id")): item
        for item in analysis_payload.get("frames", [])
        if item.get("frame_id")
    }
    frames: List[Dict[str, Any]] = []
    for index, frame in enumerate(selected_payload.get("frames", []), start=1):
        frame_id = str(frame.get("frame_id") or f"frame_{index:04d}")
        analysis = analysis_by_id.get(frame_id, {})
        prompt_analysis = str(analysis.get("ai_prompt_analysis") or "")
        sections = _parse_analysis_sections(prompt_analysis)
        merged = {
            **frame,
            "frame_id": frame_id,
            "sheet_label": analysis.get("sheet_label") or f"#{index:04d}",
            "analysis": analysis,
            "analysis_sections": sections,
            "analysis_prompt": prompt_analysis,
        }
        merged.update(_normalize_frame_analysis(merged))
        merged["categories"] = _classify_frame(merged)
        frames.append(merged)
    return frames


def build_storyboard_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        f"# {payload.get('topic', DEFAULT_TOPIC)}",
        "",
        f"- 镜头数：{payload.get('shotCount', 0)}",
        f"- 总时长：{payload.get('totalDuration', 0)} 秒",
        f"- 参考图：{len(payload.get('referenceAssets', []))} 张",
        f"- 项目目录：{payload.get('skillProjectDir', '')}",
        "",
    ]
    current_group = ""
    for shot in payload.get("storyboard_master", []):
        group = shot.get("scene_group", "")
        if group != current_group:
            current_group = group
            lines.extend(["", f"## {group}", ""])
        dependency = shot.get("reference_dependency", {})
        paths = dependency.get("reference_frame_paths") or dependency.get("market_reference_asset_paths") or []
        lines.extend(
            [
                f"### {shot.get('shot_id')} {shot.get('shot_title')}",
                "",
                f"- 画面：{shot.get('action_description', '')}",
                f"- 构图：{shot.get('composition_notes', '')}",
                f"- 运镜：{shot.get('videoPrompt', '')}",
                f"- 参考图：{', '.join(paths)}",
                "",
                shot.get("imagePrompt", ""),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_reference_assets(frames: Sequence[Dict[str, Any]], project_path: Path) -> Dict[str, Dict[str, Any]]:
    assets: Dict[str, Dict[str, Any]] = {}
    for index, frame in enumerate(frames, start=1):
        frame_id = str(frame.get("frame_id") or f"frame_{index:04d}")
        selected_path = _resolve_path(frame.get("selected_frame_path") or "", project_path)
        original_path = _resolve_path(frame.get("original_frame_path") or selected_path, project_path)
        source_path = selected_path if selected_path.exists() else original_path
        asset_id = f"ref_{index:04d}_{_safe_id(frame_id)}"
        sections = frame.get("analysis_sections", {})
        reuse_budget = _reference_reuse_budget(frame)
        assets[frame_id] = {
            "id": asset_id,
            "label": _reference_asset_label(frame, index),
            "url": _file_url(source_path),
            "thumbnail": _file_url(source_path),
            "sourcePath": str(source_path.resolve()),
            "role": "market",
            "usage": _reference_usage_text(frame),
            "status": "ready",
            "metadata": {
                "frame_id": frame_id,
                "original_frame_path": str(original_path.resolve()) if original_path else "",
                "selected_frame_path": str(selected_path.resolve()) if selected_path else "",
                "selected_frame_relative_path": frame.get("selected_frame_relative_path") or relative_path(source_path, project_path),
                "source_work_url": frame.get("source_work_url", ""),
                "source_work_id": frame.get("source_work_id", ""),
                "sheet_label": frame.get("sheet_label", ""),
                "subject": sections.get("主体", ""),
                "composition": sections.get("构图", ""),
                "lighting": sections.get("光线", ""),
                "visual_summary": frame.get("visual_summary", ""),
                "subject_type": frame.get("subject_type", ""),
                "scene_type": frame.get("scene_type", ""),
                "shot_role_tags": frame.get("shot_role_tags", []),
                "composition_tags": frame.get("composition_tags", []),
                "commercial_use_cases": frame.get("commercial_use_cases", []),
                "topic_fit_score": frame.get("topic_fit_score", 0),
                "image2_usage_weight": frame.get("image2_usage_weight", 0),
                "reference_use_policy": frame.get("reference_use_policy", ""),
                "risk_flags": frame.get("risk_flags", []),
                "reuse_budget": reuse_budget,
                "reuse_reason": _reference_reuse_reason(frame, reuse_budget),
                "usage_role": _reference_usage_role(frame),
                "usage_label": _reference_usage_label(_reference_usage_role(frame)),
                "model_reference_instruction": _reference_usage_text(frame),
            },
        }
    return assets


UNIVERSAL_STORY_GROUPS: List[Dict[str, Any]] = [
    {
        "group": "01_开场建立",
        "purpose": "建立选题的空间、环境和商业语境，提供片头与标题留白素材",
        "weight": 0.12,
        "roles": ["establishing"],
        "match_tags": ["wide", "city", "office", "depth", "copy_space"],
    },
    {
        "group": "02_主体展示",
        "purpose": "清楚呈现本选题最重要的主体、产品、人物或环境资产",
        "weight": 0.16,
        "roles": ["main_subject"],
        "match_tags": ["medium", "wide", "product", "team", "office"],
    },
    {
        "group": "03_过程动作",
        "purpose": "表现可以被剪辑使用的明确动作、操作流程或互动瞬间",
        "weight": 0.18,
        "roles": ["process_action", "people_usage"],
        "match_tags": ["medium", "handshake", "signing", "document", "tablet"],
    },
    {
        "group": "04_细节特写",
        "purpose": "提供细节、材质、手部、产品、设备或局部动作的高价值 B-roll",
        "weight": 0.16,
        "roles": ["detail_closeup"],
        "match_tags": ["closeup", "macro", "document", "signing", "texture"],
    },
    {
        "group": "05_人物或使用场景",
        "purpose": "呈现人物、用户、团队或真实使用场景，让素材更容易被商业项目复用",
        "weight": 0.14,
        "roles": ["people_usage", "main_subject", "process_action"],
        "match_tags": ["medium", "team", "meeting", "people_usage"],
    },
    {
        "group": "06_转场氛围",
        "purpose": "提供剪辑中连接段落的氛围镜头、反射、空镜、运动过渡和情绪缓冲",
        "weight": 0.08,
        "roles": ["transition_mood"],
        "match_tags": ["reflection", "silhouette", "depth", "copy_space"],
    },
    {
        "group": "07_成果情绪",
        "purpose": "表现完成、达成、品质、情绪反馈或商业结果，承担素材包的高潮画面",
        "weight": 0.10,
        "roles": ["outcome_emotion", "people_usage", "main_subject"],
        "match_tags": ["success", "applause", "handshake", "team"],
    },
    {
        "group": "08_结尾留白",
        "purpose": "提供结尾、字幕背景、品牌占位和可放标题的干净收束画面",
        "weight": 0.06,
        "roles": ["end_copy_space"],
        "match_tags": ["copy_space", "wide", "silhouette", "reflection"],
    },
]


def _build_shot_specs(
    shot_count: int,
    topic_profile: Dict[str, Any],
    frames: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    counts = _allocate_group_counts(shot_count, UNIVERSAL_STORY_GROUPS)
    specs: List[Dict[str, Any]] = []
    for group_index, template in enumerate(UNIVERSAL_STORY_GROUPS, start=1):
        count = counts[group_index - 1]
        for item_index in range(1, count + 1):
            roles = [role for role in template["roles"] if role in SHOT_ROLE_SET]
            match_tags = list(template.get("match_tags") or [])
            role = roles[(item_index - 1) % len(roles)]
            variant = _shot_variant_for_role(role, item_index, topic_profile)
            composition = _composition_for_role(role, item_index)
            spec = {
                "title": variant["title"],
                "group": template["group"],
                "purpose": template["purpose"],
                "subject": variant["subject"],
                "secondary": variant["secondary"],
                "action": variant["action"],
                "scene": variant["scene"],
                "shot_type": _shot_type_from_composition(composition),
                "camera_angle": _camera_angle_from_composition(composition),
                "composition": composition,
                "motion": _motion_for_role(role, item_index),
                "lighting": _lighting_for_role(role, topic_profile, item_index),
                "color": topic_profile["color_palette"],
                "mood": topic_profile["mood_tone"],
                "domain": topic_profile["domain"],
                "preferred_categories": list(dict.fromkeys([role, *roles, *match_tags, *_domain_preferred_tags(topic_profile)])),
                "shot_role": role,
            }
            specs.append(spec)
    return _de_duplicate_specs(specs[:shot_count])


def _allocate_group_counts(shot_count: int, templates: Sequence[Dict[str, Any]]) -> List[int]:
    if shot_count <= 0:
        return []
    raw = [shot_count * float(item.get("weight", 0)) for item in templates]
    counts = [max(1, int(value)) for value in raw]
    while sum(counts) > shot_count:
        index = max(range(len(counts)), key=lambda i: counts[i])
        if counts[index] > 1:
            counts[index] -= 1
        else:
            break
    while sum(counts) < shot_count:
        index = max(range(len(raw)), key=lambda i: raw[i] - int(raw[i]))
        counts[index] += 1
        raw[index] = int(raw[index])
    return counts


def _de_duplicate_specs(specs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[tuple[str, str, str], int] = {}
    output: List[Dict[str, Any]] = []
    for index, spec in enumerate(specs, start=1):
        key = (spec.get("group", ""), spec.get("subject", ""), spec.get("composition", ""))
        count = seen.get(key, 0)
        seen[key] = count + 1
        if count:
            spec = {
                **spec,
                "title": f"{spec['title']} 补充角度{index}",
                "composition": f"{spec['composition']}；更换主体位置、前景遮挡或留白方向，避免复制前一镜。",
            }
        output.append(spec)
    return output


def _build_topic_profile(topic: str, market_context: Dict[str, Any], frames: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    corpus = " ".join([topic, _search_text(market_context), _search_text(frames)])
    domain = _infer_topic_domain(corpus)
    short_topic = _short_topic(topic)
    style_by_domain = {
        "new_energy_vehicle": (
            "新能源汽车科技宣传片级真实摄影",
            "冷蓝银灰为主，新能源绿色光效点缀，金属、玻璃和洁净工业空间质感清楚",
            "智能、绿色、可靠、高端、面向未来城市交通",
        ),
        "festival": ("商业广告级真实摄影", "温暖高级色调，柔和主光与细腻暗部层次", "温暖、精致、情绪饱满、适合节日营销"),
        "industrial": ("企业宣传片级真实摄影", "冷白、银灰、少量蓝色辅助光，干净硬朗", "专业、可信、秩序清楚、具备科技质感"),
        "lab": ("企业科研宣传片级真实摄影", "冷白、浅灰、银色，明亮干净", "理性、精准、专业、可信"),
        "product": ("商业广告级真实摄影", "精致柔光，高级中性色，局部高光突出材质", "高级、清洁、可购买、适合产品展示"),
        "medical": ("医疗健康宣传片级真实摄影", "冷白、浅蓝、柔和干净，低对比阴影", "安全、洁净、专业、可信"),
        "education": ("教育宣传片级真实摄影", "明亮自然光，清爽柔和色调", "积极、清晰、真实、有学习氛围"),
        "tourism": ("文旅宣传片级真实摄影", "自然光、通透空气感、色彩干净", "开阔、舒适、向往、适合目的地推广"),
        "business": ("企业宣传片级真实摄影", "低饱和冷蓝灰，柔和自然光，克制对比", "专业、可信、克制、成功达成"),
        "generic": ("商业素材级真实摄影", "干净高级色调，柔和自然光，明暗关系克制", "清晰、可信、可复用、适合商业剪辑"),
    }
    visual_style, color_palette, mood_tone = style_by_domain.get(domain, style_by_domain["generic"])
    return {
        "topic": topic,
        "short_topic": short_topic,
        "domain": domain,
        "visual_style": visual_style,
        "color_palette": color_palette,
        "mood_tone": mood_tone,
        "market_context": market_context,
    }


def _infer_topic_domain(text: str) -> str:
    domain_keywords = [
        ("new_energy_vehicle", ["新能源汽车", "电动车", "智能驾驶", "自动驾驶", "智驾", "充电桩", "动力电池", "汽车电池", "车联网", "车路协同", "智能座舱", "换电站", "绿色出行", "低碳交通"]),
        ("business", ["商务", "签约", "合同", "握手", "会议", "合作", "企业"]),
        ("festival", ["中秋", "春节", "端午", "元宵", "节日", "月饼", "粽子", "团圆", "礼盒"]),
        ("industrial", ["工厂", "制造", "工业", "机械", "产线", "机器人", "自动化", "车间", "装备"]),
        ("lab", ["实验室", "科研", "研发", "新材料", "显微", "试管", "检测"]),
        ("medical", ["医疗", "医院", "医生", "护士", "健康", "药品", "康复"]),
        ("education", ["教育", "学校", "课堂", "学生", "老师", "培训", "校园"]),
        ("tourism", ["文旅", "旅游", "景区", "城市宣传", "古镇", "酒店", "航拍", "自然风光"]),
        ("product", ["产品", "电商", "包装", "礼盒", "美妆", "食品", "饮料", "静物"]),
    ]
    for domain, keywords in domain_keywords:
        if any(keyword in text for keyword in keywords):
            return domain
    return "generic"


def _short_topic(topic: str) -> str:
    text = re.sub(r"\s+", " ", str(topic or DEFAULT_TOPIC)).strip()
    return text[:24] or "商业素材"


def _build_global_style(topic_profile: Dict[str, Any]) -> str:
    return (
        f"{topic_profile['visual_style']}，{topic_profile['color_palette']}，"
        "镜头语言稳定，画面干净专业，主体和空间关系清楚，画面完整稳定，"
        "16:9 横向构图，高清细节，无品牌、无 Logo、无水印、无可读文字。"
    )


def _build_negative_prompt(topic_profile: Dict[str, Any], frames: Sequence[Dict[str, Any]]) -> str:
    base_items = [
        "可读文字",
        "Logo",
        "水印",
        "真实品牌名",
        "真实公司名",
        "乱码小字",
        "畸形手指",
        "肢体粘连",
        "主体变形",
        "过度摆拍",
        "低清晰度",
        "脏乱背景",
        "廉价塑料感",
        "过度磨皮",
        "奇怪透视",
        "重复主体",
    ]
    frame_notes: List[str] = []
    for frame in frames:
        frame_notes.extend(_as_list(frame.get("negative_prompt_notes")))
    return "不要出现：" + "、".join(_clean_negative_items([*base_items, *frame_notes])[:28]) + "。"


def _shot_variant_for_role(role: str, item_index: int, topic_profile: Dict[str, Any]) -> Dict[str, Any]:
    topic = topic_profile["short_topic"]
    domain = topic_profile["domain"]
    if domain == "new_energy_vehicle":
        return _new_energy_vehicle_shot_variant_for_role(role, item_index, topic_profile)
    if domain == "business":
        return _business_shot_variant_for_role(role, item_index, topic_profile)
    subject_word = _domain_subject_word(domain)
    scene_word = _scene_for_universal_role(domain, topic, role, item_index)
    variants = {
        "establishing": [
            ("开场建立镜头", f"{topic}的代表性环境与空间", "用宽幅画面建立主题语境和商业质感"),
            ("空间气质镜头", f"与{topic}相关的核心环境", "保留干净留白，适合片头或标题背景"),
        ],
        "main_subject": [
            ("主体展示镜头", f"{topic}的核心{subject_word}", "清楚呈现主体外观、状态和所在环境"),
            ("核心画面镜头", f"最能代表{topic}的主体画面", "让主体占据视觉中心并保持商业可用性"),
        ],
        "process_action": [
            ("过程动作镜头", f"{topic}相关的关键操作或互动", "只表现一个清楚的流程动作，便于剪辑复用"),
            ("动作推进镜头", f"{topic}中的自然动作瞬间", "主体动作克制真实，画面节奏稳定"),
        ],
        "detail_closeup": [
            ("细节特写镜头", f"{topic}相关的材质、道具或局部细节", "突出纹理、手部、结构或产品细节"),
            ("局部质感镜头", f"{topic}的高价值细节元素", "利用浅景深突出细节并弱化背景干扰"),
        ],
        "people_usage": [
            ("人物使用场景", f"与{topic}相关的人物或用户场景", "人物自然参与主题流程，动作真实可信"),
            ("真实应用镜头", f"{topic}中的使用者与环境", "体现真实使用语境和商业复用价值"),
        ],
        "transition_mood": [
            ("转场氛围镜头", f"{topic}的环境光影、反射或空镜", "提供段落衔接和情绪缓冲"),
            ("氛围过渡镜头", f"{topic}相关空间中的光影层次", "减少主体密度，保留剪辑呼吸感"),
        ],
        "outcome_emotion": [
            ("成果情绪镜头", f"{topic}的完成状态、成果或积极反馈", "呈现达成、品质、满意或收束情绪"),
            ("结果表达镜头", f"{topic}带来的结果画面", "画面积极可信，可作为素材包高潮镜头"),
        ],
        "end_copy_space": [
            ("结尾留白镜头", f"{topic}的干净背景和收束画面", "保留大面积干净区域，适合放标题或片尾"),
            ("收尾主视觉", f"{topic}相关的安静完整画面", "主体不过度拥挤，画面可作为结尾背景"),
        ],
    }
    title_suffix, subject, action = variants.get(role, variants["main_subject"])[(item_index - 1) % 2]
    return {
        "title": f"{topic}{title_suffix}{item_index}",
        "subject": subject,
        "secondary": _secondary_for_universal(topic_profile, role),
        "action": action,
        "scene": scene_word,
    }


def _new_energy_vehicle_shot_variant_for_role(role: str, item_index: int, topic_profile: Dict[str, Any]) -> Dict[str, Any]:
    variants = {
        "establishing": [
            ("智慧城市道路建立", "新能源智能汽车在城市主干道与高架道路中行驶", "用宽幅城市道路建立智能出行和车路协同语境", "现代城市道路、高架桥、绿化带、道路传感器和远处商务楼宇"),
            ("绿色交通生态建立", "电动车、风机、光伏板和城市道路形成绿色交通主视觉", "建立零排放、绿色能源与智慧出行的整体关系", "开阔风光能源场、城市远景、干净天空和车辆行驶道路"),
            ("充电网络建立", "多辆新能源汽车停靠在现代充电站与停车区", "展示公共补能网络和运营规模", "城市充电站、整齐停车位、充电桩阵列和玻璃顶棚"),
            ("智能制造基地建立", "新能源汽车工厂产线与自动化机械臂形成工业远景", "让客户看到可用于车企宣传和制造升级的开场画面", "明亮洁净汽车工厂、机械臂、车身骨架和生产通道"),
        ],
        "main_subject": [
            ("新能源整车主体", "一辆无品牌新能源轿车或 SUV 作为画面核心", "清楚呈现车辆外观、科技灯带和城市道路语境", "城市道路、桥梁或充电区，车辆居中或三分构图"),
            ("自动驾驶透明车身", "透明车身中的电池包、电机和传感器结构", "展示智能电动车的核心技术卖点", "深色科技背景或道路场景，车身内部结构以蓝绿光效呈现"),
            ("充电桩主体展示", "现代快充桩与正在充电的新能源车", "展示补能基础设施和车桩连接关系", "城市充电站、干净地面、玻璃棚和绿化背景"),
            ("动力电池主体展示", "整齐排列的动力电池包、电芯或电池模组", "突出新能源汽车电池技术和储能价值", "洁净产线、实验台或科技展示台，冷白工业光"),
            ("车路协同主视觉", "道路中车辆、车道识别线和联网交通数据光效", "表现智慧交通系统对车辆和道路的协同感知", "城市道路俯视或车内 HUD 视角，蓝绿色数据线清晰但不可读"),
        ],
        "process_action": [
            ("车辆智能巡航", "新能源车在道路上保持车道并识别前车", "呈现自动驾驶、辅助驾驶和安全跟车功能", "城市道路或高速道路，车道线、感知光圈和前车关系清楚"),
            ("充电连接动作", "充电枪插入车辆充电口并形成稳定能量光效", "表现用户最直观的补能流程", "近景车辆侧后方、充电桩和线缆，背景干净"),
            ("自动泊车入位", "新能源车在停车场自动识别车位并缓慢入位", "表现智慧停车和自动泊车功能", "停车场俯视或中景，车位线、车辆轨迹和桩位关系清楚"),
            ("电池产线流转", "电池模组在洁净产线上通过传送和检测工位", "表现动力电池制造、检测和质量控制", "明亮车间、输送线、机械手和排列电芯"),
            ("机械臂装配车身", "自动化机械臂围绕白车身完成焊接或装配", "表现智能制造和汽车工厂生产效率", "现代汽车制造车间、黄色或白色机械臂、车身框架"),
            ("工程师调试系统", "工程师在透明屏或平板上查看车辆能源与智驾模型", "表现研发、运维和数字化管理能力", "实验室、控制室或风光能源现场，界面抽象不可读"),
        ],
        "detail_closeup": [
            ("充电口特写", "车辆充电口、充电枪、线缆和指示灯局部", "突出补能动作和可剪辑的细节 B-roll", "浅景深近景，车身漆面、接口和绿色能量光效清楚"),
            ("电芯排列特写", "圆柱电芯、方形电池模组或电池包结构局部", "突出动力电池材料和精密制造质感", "冷白实验光或产线灯光，排列秩序和金属质感清楚"),
            ("传感器与 HUD 特写", "车内前挡风 HUD、车道识别线和驾驶辅助图形", "展示智能座舱、辅助驾驶和人机交互", "车内驾驶视角，前方道路清楚，界面抽象无可读文字"),
            ("底盘电池结构特写", "透明底盘中的电池包、电机与线束结构", "展示电驱、电池和安全结构", "深色或道路背景，结构光效克制真实"),
            ("机械臂末端特写", "机械臂夹具、焊接点、车身边缘或检测设备局部", "突出智能制造和精密装配细节", "工厂近景，金属反光和工业灯光稳定"),
        ],
        "people_usage": [
            ("工程师能源沙盘", "工程师围绕风光储充或城市交通模型进行讨论", "提供企业方案、能源规划和项目汇报类可售画面", "明亮办公室或实验室，模型、平板和抽象数据光效同框"),
            ("研发人员调试智驾", "研发人员在控制台或透明屏前调试车辆模型", "表现车企研发、AI 算法和数字孪生能力", "智能实验室、屏幕光、车辆模型或数据界面，人物动作自然"),
            ("运维人员巡检风电光伏", "穿工装的运维人员在风机或光伏场旁查看设备", "补齐低碳能源和绿色交通基础设施的人物场景", "户外风光能源场、自然光、设备纵深和安全工装"),
            ("用户补能场景", "用户或车辆在充电站完成停车、插枪或等待充电", "表现真实使用场景和公共出行服务", "城市充电站、车辆、桩位、停车线和生活化环境"),
        ],
        "transition_mood": [
            ("道路数据流转场", "夜色或俯视道路上的蓝绿数据流与车辆轨迹", "连接智驾、车联网和智慧城市段落", "城市道路、车道线、光轨和低主体密度环境"),
            ("能源光效转场", "风机、光伏、水面或山谷与绿色能量光线形成过渡", "连接新能源发电、储能和车辆使用", "自然能源场景、天空留白、蓝绿光效克制"),
            ("工厂通道转场", "洁净产线通道、设备灯光和机械臂轮廓形成纵深", "连接研发、生产和质量控制段落", "现代车间通道、冷白灯光、金属反射和空间线条"),
            ("城市车流氛围", "城市道路车流与智能驾驶光效形成安静氛围镜头", "作为片中段落转换和情绪缓冲", "高架、桥梁、车流、建筑剪影和蓝绿色车道光线"),
        ],
        "outcome_emotion": [
            ("智慧出行成果", "新能源车平稳驶向开阔城市道路或未来桥梁", "表现智能交通落地后的安全、高效和舒适", "开阔道路、城市天际线、自然光和车辆主视觉"),
            ("绿色能源闭环", "电动车、充电桩、风机、光伏和储能系统同框", "表现从清洁能源到绿色出行的完整闭环", "能源场或充电站，元素清晰但不过度堆叠"),
            ("智能制造成果", "完整车身在自动化产线中完成下线或检测", "表现车企制造能力和产业升级结果", "现代工厂、机械臂、车身和洁净空间"),
            ("运营网络成果", "大型充电站或停车场中多车有序补能", "表现充电运营、城市服务和规模化部署", "俯视或中远景充电场站，车位与桩位秩序清楚"),
        ],
        "end_copy_space": [
            ("结尾城市道路留白", "新能源车驶向远处城市天际线，画面保留干净天空或道路留白", "提供可放品牌标题的片尾主视觉", "城市道路、桥梁、天空和大面积干净区域"),
            ("结尾充电站留白", "现代充电站一侧排列充电桩，另一侧保留干净空间", "适合运营商、车企或能源企业片尾", "充电站棚架、车辆局部、地面反光和简洁背景"),
            ("结尾能源场留白", "风机或光伏场与远处道路形成安静收束画面", "表达低碳、零排放和绿色交通愿景", "风光能源场、天空、草地或水面，主体偏侧"),
        ],
    }
    options = variants.get(role, variants["main_subject"])
    title_suffix, subject, action, scene = options[(item_index - 1) % len(options)]
    return {
        "title": f"{title_suffix}{item_index}",
        "subject": subject,
        "secondary": _secondary_for_universal(topic_profile, role),
        "action": action,
        "scene": scene,
    }


def _business_shot_variant_for_role(role: str, item_index: int, topic_profile: Dict[str, Any]) -> Dict[str, Any]:
    variants = {
        "establishing": [
            ("商务楼宇建立", "现代城市商务楼宇、玻璃幕墙和高层办公区外景", "建立企业合作发生的城市商务语境，画面只呈现空间、建筑和光影"),
            ("会议空间空镜", "明亮会议室、长桌、窗边城市光和整齐文件", "用空镜呈现签约前的正式空间和秩序感，画面聚焦会前准备"),
            ("办公大厅到访", "现代企业大厅、前台区域、玻璃门和商务团队远景", "表现合作方抵达企业空间，人物仅作为环境尺度"),
            ("走廊进入会议", "玻璃走廊、会议室入口和携带资料的商务人员背影", "用纵深动线引入会议流程，避免提前出现达成动作"),
            ("城市窗景转场", "高层窗外城市天际线、会议桌前景和玻璃反射", "用窗光和城市背景建立高端商务氛围"),
            ("桌面准备建立", "空会议桌、无字文件夹、签字笔和整洁座位", "表现会前准备完成，保留片头留白和正式仪式感"),
        ],
        "main_subject": [
            ("签约主体展示", "会议桌两侧的双方代表、空白合同文件和正式座席关系", "清楚呈现合作双方进入正式会议的主体关系"),
            ("资料主体展示", "合同文件、平板设备、签字笔和整洁会议桌", "展示签约流程核心物件和专业准备状态"),
            ("负责人入座", "双方负责人在会议桌旁入座并查看资料", "表现正式沟通开始前的克制状态"),
            ("团队关系展示", "双方团队围坐会议桌形成清楚左右关系", "呈现合作双方团队结构，不表现签约完成"),
            ("方案确认主体", "商务代表查看平板和文件资料", "展示方案确认与合作推进的核心画面"),
        ],
        "process_action": [
            ("资料审阅动作", "商务人士翻阅空白合同和资料文件", "只表现审阅、翻页和确认动作"),
            ("平板说明动作", "两位商务人士围绕平板展示抽象方案", "表现方案沟通，不出现可读文字"),
            ("文件递交动作", "一方把文件夹递给对方团队成员", "表现签约前资料交接流程"),
            ("签字准备动作", "签字笔靠近空白合同签署区域", "表现落笔前一刻的流程张力"),
            ("合同签署动作", "商务负责人用签字笔在空白合同区域签署", "表现正式签约动作，避免可读签名"),
            ("文件整理动作", "团队成员把签署资料整理到会议桌中央", "表现流程推进和会议秩序"),
        ],
        "detail_closeup": [
            ("签字笔细节", "黑色签字笔、白色纸面和手部局部", "突出笔尖、手指和纸张纹理"),
            ("合同页细节", "空白合同页边缘、文件夹和袖口局部", "突出纸张、布料和桌面材质"),
            ("资料交接细节", "手部递交文件夹的局部动作", "突出手部、文件边缘和浅景深"),
            ("签署局部细节", "钢笔落笔、指尖和不可读签署区域", "突出正式签约流程的微距细节"),
            ("桌面秩序细节", "会议桌上的签字笔、文件夹和玻璃杯轮廓", "突出整洁专业的桌面质感"),
        ],
        "people_usage": [
            ("会议讨论场景", "双方团队围绕会议桌讨论合作方案", "人物自然倾听、翻页和交流"),
            ("双人方案确认", "两位商务代表在窗边查看平板资料", "表现合作沟通中的自然互动"),
            ("团队入座场景", "多位商务人士进入会议室并整理座位", "表现正式会议开始前的真实流程"),
            ("执行沟通场景", "签约后团队围绕文件继续沟通执行安排", "表现合作落地而非重复握手"),
            ("办公区协作场景", "商务团队在开放办公区查看资料和显示器", "表现后续执行和团队协作"),
        ],
        "transition_mood": [
            ("玻璃反射转场", "玻璃幕墙反射、商务人影轮廓和城市光线", "提供段落衔接的低主体密度画面"),
            ("会议室空镜转场", "空会议室、长桌、窗光和整齐座椅", "表现正式空间的安静呼吸感"),
            ("走廊光影转场", "办公走廊、玻璃隔断和远处会议室门", "用纵深线条连接会议流程"),
            ("桌面光影转场", "文件夹、签字笔和桌面反光的安静局部", "提供签约段落之间的剪辑缓冲"),
        ],
        "outcome_emotion": [
            ("正式握手达成", "两位负责人在会议桌旁握手，桌面保留签署文件", "表现签约完成后的合作达成"),
            ("团队认可鼓掌", "会议室内团队成员克制鼓掌祝贺", "表现成功达成后的积极反馈"),
            ("签约文件完成", "签署完成的文件夹放在桌面中央，人物在背景交流", "表现合同流程完成"),
            ("合作确认合影", "双方团队在会议室形成正式合作站位", "表现合作成功但避免夸张摆拍"),
            ("窗边达成交流", "两位负责人在窗边自然交流并轻微点头", "表现达成后的信任与确认"),
        ],
        "end_copy_space": [
            ("结尾城市留白", "高层窗景、干净会议桌和大面积明亮留白", "提供可放标题的宣传片结尾背景"),
            ("会议室收束空镜", "签约完成后的空会议桌、文件夹和窗边光线", "表现流程结束后的安静空间"),
            ("商务楼宇结尾", "现代办公楼远景、天空和玻璃反射", "提供企业宣传片片尾主视觉"),
            ("文件留白结尾", "桌面文件偏侧摆放，背景是柔和城市窗光", "保留干净区域用于标题或品牌占位"),
            ("团队背影收束", "商务团队远景背影看向城市窗景", "表现合作后的未来展望"),
        ],
    }
    options = variants.get(role, variants["main_subject"])
    title_suffix, subject, action = options[(item_index - 1) % len(options)]
    return {
        "title": f"{title_suffix}{item_index}",
        "subject": subject,
        "secondary": _secondary_for_universal(topic_profile, role),
        "action": action,
        "scene": _business_scene_for_subject(subject, role, topic_profile, item_index),
    }


def _business_scene_for_subject(subject: str, role: str, topic_profile: Dict[str, Any], item_index: int) -> str:
    if any(keyword in subject for keyword in ["楼宇", "幕墙", "外景", "办公楼"]):
        return "现代城市商务楼宇外立面、玻璃幕墙、高层办公区和城市天际线"
    if any(keyword in subject for keyword in ["会议室", "长桌", "会议桌", "座席", "围坐"]):
        return "明亮现代会议室、长桌、落地窗、玻璃隔断和干净桌面"
    if any(keyword in subject for keyword in ["大厅", "前台", "玻璃门"]):
        return "现代企业大堂、前台接待区、玻璃门、绿植和地面反光"
    if any(keyword in subject for keyword in ["走廊", "会议室入口"]):
        return "玻璃办公走廊、会议室入口、墙面反射和清楚纵深线条"
    if any(keyword in subject for keyword in ["窗外", "窗景", "窗边", "城市天际线"]):
        return "高层窗边商务空间、城市天际线、玻璃反射和柔和自然窗光"
    if any(keyword in subject for keyword in ["桌面", "文件夹", "签字笔", "合同文件", "纸面"]):
        return "会议桌桌面、整洁座位、窗边自然光和无字纸质文件"
    if any(keyword in subject for keyword in ["办公区", "开放办公区", "显示器"]):
        return "现代开放办公区、玻璃隔断、电脑设备和自然窗光"
    if any(keyword in subject for keyword in ["大厅", "接待"]):
        return "企业接待空间、玻璃入口和明亮商务公共区域"
    return _scene_for_universal_role("business", topic_profile["short_topic"], role, item_index)


def _domain_subject_word(domain: str) -> str:
    return {
        "new_energy_vehicle": "车辆、能源设备、产线或人员",
        "business": "合作主体",
        "festival": "节日主体",
        "industrial": "设备、空间或人员",
        "lab": "科研主体",
        "product": "产品主体",
        "medical": "医疗健康主体",
        "education": "学习主体",
        "tourism": "目的地画面",
    }.get(domain, "核心主体")


def _domain_scene_word(domain: str, topic: str) -> str:
    return {
        "new_energy_vehicle": f"与{topic}相关的智慧道路、补能网络、汽车工厂、动力电池或绿色能源空间",
        "business": f"与{topic}相关的现代商业空间或合作场景",
        "festival": f"与{topic}相关的节日生活、礼赠或氛围场景",
        "industrial": f"与{topic}相关的现代生产、展示或执行空间",
        "lab": f"与{topic}相关的干净研发、实验或展示空间",
        "product": f"与{topic}相关的商业展示、使用或静物环境",
        "medical": f"与{topic}相关的洁净专业医疗健康空间",
        "education": f"与{topic}相关的学习、培训或校园空间",
        "tourism": f"与{topic}相关的城市、景区、建筑或自然环境",
    }.get(domain, f"与{topic}相关的真实商业素材场景")


def _scene_for_universal_role(domain: str, topic: str, role: str, item_index: int) -> str:
    domain_scenes = {
        "new_energy_vehicle": {
            "establishing": ["现代城市智慧道路、高架桥、车路协同设备和新能源车行驶环境", "风电光伏能源场、城市道路和零排放绿色交通环境"],
            "main_subject": ["新能源整车、透明电驱结构、充电桩或动力电池展示空间", "车辆主体与道路、能源或工厂环境同框的科技宣传场景"],
            "process_action": ["自动驾驶巡航、车道识别、充电连接、自动泊车或产线装配流程现场", "车路协同、补能、检测、装配和工程师调试的过程场景"],
            "detail_closeup": ["充电口、电池模组、HUD、传感器、底盘电池或机械臂局部细节", "车辆科技组件、能源接口和精密制造结构特写"],
            "people_usage": ["工程师、运维人员或用户参与智驾研发、能源运营和补能服务场景", "车企研发、能源规划、充电运维和真实出行服务空间"],
            "transition_mood": ["道路数据流、能源光效、工厂通道、车流光轨和低主体密度转场画面", "蓝绿科技光效连接车辆、道路、能源和制造段落"],
            "outcome_emotion": ["智慧出行成果、绿色能源闭环、车辆下线和充电网络规模化部署场景", "智能交通落地、低碳出行和产业升级结果画面"],
            "end_copy_space": ["城市道路、充电站、能源场或工厂空间中的干净标题留白画面", "新能源车、风光能源和智慧城市背景形成片尾主视觉"],
        },
        "business": {
            "establishing": ["现代城市商务楼宇外立面、玻璃幕墙和高层办公窗景", "明亮会议室外侧、城市天际线和企业办公空间"],
            "main_subject": ["现代会议室、签约桌、玻璃隔断和窗边商务空间", "企业办公区、会议桌、文件资料和自然窗光"],
            "process_action": ["会议桌旁的资料交接、方案确认或合作沟通现场", "玻璃会议室内的签约准备、讨论和互动流程"],
            "detail_closeup": ["干净会议桌、纸质文件、签字笔、袖口和桌面材质细节", "商务文件、笔尖、手部动作和浅景深桌面局部"],
            "people_usage": ["双方团队围绕会议桌沟通、入座、倾听或确认方案", "商务团队在会议室、走廊或办公区自然协作"],
            "transition_mood": ["玻璃反射、窗边逆光、会议室空镜和城市光影层次", "办公室走廊、幕墙倒影和低主体密度转场空间"],
            "outcome_emotion": ["签约完成后的握手、鼓掌、团队认可和桌面文件同框", "合作达成后的会议室、窗边和团队成功氛围"],
            "end_copy_space": ["高层窗边、干净会议桌和大面积明亮留白背景", "现代商务空间空镜、城市窗景和可放标题的结尾画面"],
        },
        "festival": {
            "establishing": ["节日餐桌、家居空间、礼赠陈列和柔和暖光环境", "节庆布置、生活场景和干净留白背景"],
            "main_subject": ["节日主体、礼盒包装、食物或手作道具的商业陈列空间", "节庆产品与生活道具组合的真实广告场景"],
            "process_action": ["手部制作、摆放、包装、分享或打开礼盒的自然动作现场", "节日准备流程、家庭互动和礼赠动作场景"],
            "detail_closeup": ["食物纹理、包装材质、手部动作、蒸汽或布料细节", "节庆道具、礼盒边缘、食材和浅景深局部"],
            "people_usage": ["人物分享礼物、准备节庆餐桌或家庭互动的生活场景", "节日用户场景、手部递送和温暖生活空间"],
            "transition_mood": ["暖色灯光、窗边反射、节日装饰虚化和空镜氛围", "生活空间中的柔和光影、桌面留白和装饰层次"],
            "outcome_emotion": ["礼赠完成、分享完成、餐桌成品和温暖情绪反馈", "节日团聚、产品完成状态和温馨商业画面"],
            "end_copy_space": ["干净桌面、暖色背景和可放标题的节日收束画面", "节庆元素偏一侧、大面积背景留白的结尾主视觉"],
        },
        "industrial": {
            "establishing": ["现代工厂产线、自动化车间、设备阵列和工业空间纵深", "干净制造空间、机械设备和秩序化生产环境"],
            "main_subject": ["工业设备主体、产线模块、机器人或操作工位展示空间", "设备与生产环境同框的企业宣传片场景"],
            "process_action": ["机械运行、人员操作、质检、传送或设备调试流程现场", "产线执行、按钮操作、零件流转和人员协作场景"],
            "detail_closeup": ["金属结构、按钮、机械臂、零件表面和工业材质局部", "设备边缘、工装手套、传感器或精密结构特写"],
            "people_usage": ["工程师巡检、团队协作、看板确认或设备旁沟通现场", "现代车间中的人员动线、操作和安全协作场景"],
            "transition_mood": ["设备灯光、金属反射、产线纵深和低主体密度空镜", "车间通道、机械轮廓和冷色工业光影转场"],
            "outcome_emotion": ["产品下线、质检通过、设备稳定运行或团队认可画面", "工业项目完成、产线顺畅和企业成果展示场景"],
            "end_copy_space": ["产线远景、设备轮廓和可放标题的干净工业背景", "现代工厂空间留白、冷色光线和结尾主视觉"],
        },
        "lab": {
            "establishing": ["洁净研发实验室、仪器阵列、实验台和冷白空间层次", "科研中心走廊、透明实验区和明亮专业环境"],
            "main_subject": ["实验仪器、样品容器、研究设备和干净实验台展示空间", "科研主体与实验环境同框的企业研发宣传场景"],
            "process_action": ["实验操作、样品检测、仪器调试或研发人员协作现场", "手部取样、观察记录和设备运行的专业流程"],
            "detail_closeup": ["试管、样品、显微结构、玻璃器皿和仪器材质特写", "实验台局部、精密设备边缘和浅景深科研细节"],
            "people_usage": ["研发人员在实验室内沟通、操作或查看样品的真实场景", "科研团队围绕仪器、实验台或显示设备协作"],
            "transition_mood": ["实验室玻璃反射、冷白灯光、仪器轮廓和空镜转场", "洁净空间中的光影层次、透明材质和低主体密度画面"],
            "outcome_emotion": ["检测完成、样品确认、研发成果展示或团队认可画面", "科研项目阶段性成果和专业可信的完成状态"],
            "end_copy_space": ["洁净实验空间、仪器轮廓和可放标题的冷白留白背景", "实验台空镜、柔和灯光和结尾收束画面"],
        },
        "product": {
            "establishing": ["产品广告级陈列空间、干净背景和商业布光环境", "静物展示台、柔和背景、包装或使用场景建立画面"],
            "main_subject": ["核心产品、包装形态、材质表面和商业展示空间", "产品主体居中或偏侧的高级广告静物场景"],
            "process_action": ["打开包装、拿取产品、使用产品或摆放陈列的自然动作", "产品使用过程、手部互动和道具协同场景"],
            "detail_closeup": ["产品材质、边缘、包装纹理、液体高光或功能细节特写", "商业微距、浅景深和高光控制的产品局部"],
            "people_usage": ["用户手部使用产品、生活化接触或真实消费场景", "人物与产品自然互动的商业可售画面"],
            "transition_mood": ["产品高光、背景虚化、反射、布料或道具空镜转场", "低主体密度的广告光影和质感过渡画面"],
            "outcome_emotion": ["产品完成展示、使用后状态、精致陈列或满意反馈画面", "产品价值结果、整洁桌面和商业成果表达"],
            "end_copy_space": ["产品偏侧摆放、大面积干净背景和可放标题留白", "广告级结尾主视觉、柔光背景和简洁静物构图"],
        },
        "medical": {
            "establishing": ["洁净医疗健康空间、明亮走廊、诊疗区和浅蓝白环境", "专业医疗机构内的干净空间层次和安全氛围"],
            "main_subject": ["医疗健康主体、专业设备、诊疗台或护理环境展示空间", "健康服务主体与洁净空间同框的宣传片场景"],
            "process_action": ["检查、护理、康复训练、设备操作或健康咨询流程现场", "医护人员手部操作、患者配合和专业服务动作"],
            "detail_closeup": ["医疗器械、手套、检测设备、药品轮廓或康复器材局部", "洁净材质、浅景深和专业细节特写"],
            "people_usage": ["医护人员、患者或健康服务人员自然互动的真实场景", "咨询、护理、康复或检查中的人物关系画面"],
            "transition_mood": ["医疗空间空镜、玻璃反射、柔和灯光和洁净转场", "低对比浅蓝白光影、走廊纵深和安全感氛围"],
            "outcome_emotion": ["检查完成、康复进展、健康反馈或安心交流画面", "专业服务结果和温和可信的情绪收束"],
            "end_copy_space": ["洁净背景、医疗空间轮廓和可放标题的浅色留白", "健康宣传片结尾主视觉、柔和光线和干净空间"],
        },
        "education": {
            "establishing": ["明亮校园、教室、培训空间或学习环境建立画面", "教育机构空间、自然光和清爽学习氛围"],
            "main_subject": ["课堂主体、学习道具、教学设备或培训场景展示空间", "学习主体与环境同框的教育宣传片画面"],
            "process_action": ["书写、讲解、讨论、实验、阅读或互动学习流程现场", "师生互动、手部操作和学习任务推进场景"],
            "detail_closeup": ["书本、笔记、手写动作、教学道具或屏幕边缘特写", "学习用品、纸张纹理和浅景深细节"],
            "people_usage": ["学生、老师或培训用户在真实学习环境中互动", "小组讨论、课堂提问或学习陪伴场景"],
            "transition_mood": ["教室空镜、窗边自然光、书桌留白和校园转场", "学习空间中的柔和光影、走廊或桌面空镜"],
            "outcome_emotion": ["完成练习、讨论达成、课堂反馈或积极学习成果画面", "教育结果、成长氛围和真实情绪收束"],
            "end_copy_space": ["书桌、教室背景、校园光线和可放标题留白", "教育宣传结尾主视觉、清爽背景和安静空间"],
        },
        "tourism": {
            "establishing": ["城市地标、景区建筑、自然风光或目的地宽幅建立画面", "文旅目的地远景、天空留白和空间层次"],
            "main_subject": ["核心景观、建筑、街区、酒店或文旅体验主体展示空间", "目的地主体与真实环境同框的商业素材场景"],
            "process_action": ["游客行走、入住、体验、拍照、游览或服务流程现场", "文旅活动中的自然动作和空间推进画面"],
            "detail_closeup": ["建筑纹理、手部体验、地方物件、美食或自然细节特写", "目的地材质、光影和浅景深局部"],
            "people_usage": ["游客、服务人员或体验者在真实目的地中互动", "人物尺度与景观空间关系清楚的文旅场景"],
            "transition_mood": ["街巷光影、水面反射、天空、窗景或自然空镜转场", "低主体密度的目的地氛围和呼吸感画面"],
            "outcome_emotion": ["抵达、体验完成、放松、眺望或向往感结果画面", "旅行情绪、目的地价值和舒适收束"],
            "end_copy_space": ["景观偏侧、大面积天空或墙面留白的结尾画面", "文旅宣传片结尾主视觉、自然光和干净背景"],
        },
    }
    generic_scenes = {
        "establishing": [f"与{topic}相关的代表性环境、空间入口和商业语境", f"{topic}的宽幅环境、背景留白和空间层次"],
        "main_subject": [f"{topic}的核心主体展示空间", f"最能代表{topic}的真实商业素材场景"],
        "process_action": [f"{topic}相关的关键操作、互动或流程现场", f"{topic}中的自然动作和过程推进场景"],
        "detail_closeup": [f"{topic}相关的材质、道具、手部或局部细节空间", f"{topic}的高价值细节和浅景深局部"],
        "people_usage": [f"{topic}相关的人物、用户或真实使用场景", f"{topic}中的人物参与和环境关系"],
        "transition_mood": [f"{topic}相关的光影、反射、空镜或转场空间", f"{topic}的低主体密度氛围场景"],
        "outcome_emotion": [f"{topic}的完成状态、成果展示或积极反馈场景", f"{topic}带来的结果画面和商业收束"],
        "end_copy_space": [f"{topic}的干净背景、结尾留白和标题占位画面", f"{topic}相关的安静收束空间"],
    }
    scenes = domain_scenes.get(domain, generic_scenes).get(role, [f"与{topic}相关的真实商业素材场景"])
    return _pick_variant(scenes, item_index)


def _secondary_for_universal(topic_profile: Dict[str, Any], role: str) -> List[str]:
    domain_items = {
        "new_energy_vehicle": ["车辆主体", "道路数据", "充电设备", "动力电池", "绿色能源", "工业空间"],
        "business": ["文件资料", "桌面道具", "空间玻璃", "人物互动"],
        "festival": ["节日道具", "礼赠元素", "环境光影", "生活场景"],
        "industrial": ["设备结构", "空间纵深", "操作细节", "人员动线"],
        "lab": ["实验台", "样品器具", "仪器细节", "洁净背景"],
        "product": ["产品材质", "包装形态", "使用道具", "柔和背景"],
        "medical": ["洁净空间", "专业器具", "人物动作", "柔和光线"],
        "education": ["学习道具", "空间环境", "人物互动", "自然光线"],
        "tourism": ["环境层次", "建筑线条", "人物尺度", "天空或自然光"],
    }
    items = list(domain_items.get(topic_profile["domain"], ["核心主体", "环境层次", "动作细节", "干净背景"]))
    if role in {"detail_closeup", "process_action"}:
        items = ["局部细节", "材质纹理", "手部或操作", *items]
    if role in {"end_copy_space", "transition_mood", "establishing"}:
        items = ["留白区域", "环境层次", "光影变化", *items]
    return _unique_items(items)[:4]


def _composition_for_role(role: str, item_index: int) -> str:
    options = {
        "establishing": [
            "宽幅远景，主体空间位于画面中部，保留天空、墙面或背景留白，空间层次完整",
            "中远景建立镜头，前景有轻微环境遮挡，中景主体清楚，背景提供主题语境",
        ],
        "main_subject": [
            "中景构图，主体位于画面中心偏一侧，前中后景关系清楚，边缘保留真实环境细节",
            "宽幅中景，主体占画面中部，左右留出可剪辑空间，背景不过度虚化",
        ],
        "process_action": [
            "中近景，动作发生在画面中心，前景道具和主体手部形成清楚视觉引导",
            "平视中景，主体动作从画面一侧进入中心，背景保持稳定层次",
        ],
        "detail_closeup": [
            "特写或微距，主体局部占据画面中心，浅景深突出材质纹理和动作细节",
            "近景局部裁切，主体细节清晰，背景虚化成干净色块，避免信息杂乱",
        ],
        "people_usage": [
            "中景或中近景，人物与主体形成明确互动关系，表情自然，环境完整",
            "平视观察构图，人物位于画面三分之一处，主体动作和空间关系清楚",
        ],
        "transition_mood": [
            "空镜或半空镜构图，环境光影、反射或前景遮挡形成转场层次",
            "中远景，主体密度较低，保留干净呼吸空间和方向性线条",
        ],
        "outcome_emotion": [
            "中景构图，完成状态或情绪反馈位于视觉中心，背景保留主题环境",
            "宽幅中景，主体关系稳定，画面有积极收束感和正式商业氛围",
        ],
        "end_copy_space": [
            "宽幅留白构图，主体偏左或偏右，大面积干净区域可放标题或片尾信息",
            "远景或中远景，主体不过度拥挤，背景完整安静，画面适合作为结尾背景",
        ],
    }
    return _pick_variant(options.get(role, options["main_subject"]), item_index)


def _motion_for_role(role: str, item_index: int) -> str:
    options = {
        "establishing": ["缓慢推近", "稳定横移", "轻微上升"],
        "main_subject": ["缓慢推近", "静态微推", "轻微环绕"],
        "process_action": ["轻微跟随", "稳定侧移", "缓慢推入"],
        "detail_closeup": ["微距推近", "轻微焦点转移", "固定近景"],
        "people_usage": ["平视微推", "轻微横移", "稳定跟拍"],
        "transition_mood": ["缓慢横移", "轻微变焦", "静态微推"],
        "outcome_emotion": ["缓慢推近", "稳定横移", "轻微拉近"],
        "end_copy_space": ["静态微推", "缓慢横移", "轻微上升"],
    }
    return _pick_variant(options.get(role, ["缓慢推近"]), item_index)


def _lighting_for_role(role: str, topic_profile: Dict[str, Any], item_index: int) -> str:
    if role in {"detail_closeup", "process_action"}:
        return "柔和主光突出主体局部，高光克制，阴影干净，材质和动作细节清楚"
    if role in {"establishing", "end_copy_space", "transition_mood"}:
        return "自然光或环境光形成稳定空间层次，保留干净留白和轻微光影变化"
    return "柔和自然光与克制商业布光结合，主体受光清楚，背景不过曝不杂乱"


def _domain_preferred_tags(topic_profile: Dict[str, Any]) -> List[str]:
    return {
        "new_energy_vehicle": ["industrial", "product", "process_action", "detail_closeup", "establishing", "people_usage"],
        "business": ["business", "people_usage", "process_action", "detail_closeup"],
        "festival": ["festival", "product", "people_usage", "detail_closeup"],
        "industrial": ["industrial", "process_action", "establishing", "detail_closeup"],
        "lab": ["lab", "detail_closeup", "process_action", "people_usage"],
        "product": ["product", "detail_closeup", "main_subject", "end_copy_space"],
        "medical": ["medical", "people_usage", "detail_closeup", "process_action"],
        "education": ["education", "people_usage", "process_action", "establishing"],
        "tourism": ["tourism", "establishing", "transition_mood", "end_copy_space"],
    }.get(topic_profile["domain"], ["main_subject", "process_action", "detail_closeup"])


def _reference_reuse_budget(frame: Dict[str, Any]) -> int:
    policy = str(frame.get("reference_use_policy") or "image2_reference")
    risk_text = " ".join(str(item) for item in _as_list(frame.get("risk_flags")))
    if policy in {"exclude", "evidence_only"}:
        return 0
    if any(keyword in risk_text for keyword in ["水印", "Logo", "文字", "多宫格", "低相关", "版权"]):
        return 0
    weight = _clamp_float(frame.get("image2_usage_weight"), 0.0, 1.0, default=0.5)
    if weight <= 0:
        return 0
    if policy in {"composition_only", "style_only"}:
        return 1

    tags = _frame_match_tags(frame)
    topic_fit = int(_clamp_float(frame.get("topic_fit_score"), 0, 100, default=60))
    if _is_detail_reference(frame, tags):
        return 1

    budget = 1
    if weight >= 0.72 and topic_fit >= 70 and tags & {"establishing", "process_action", "people_usage", "transition_mood", "outcome_emotion", "wide", "depth", "meeting", "handshake"}:
        budget += 1
    if weight >= 0.86 and topic_fit >= 82 and tags & {"establishing", "process_action", "people_usage", "wide", "depth", "handshake", "meeting", "team", "success"}:
        budget += 1
    return max(0, min(3, budget))


def _reference_reuse_reason(frame: Dict[str, Any], budget: int) -> str:
    if budget <= 0:
        return "低相关、风险或证据类参考帧，仅保留在 referenceAssets 中，不进入 image2 绑定。"
    usage_role = _reference_usage_role(frame)
    if budget == 1:
        return f"普通参考帧，主要用于{usage_role}，只绑定到最匹配的一个镜头。"
    return f"高价值参考帧，适合{usage_role}，可在 {budget} 个同场景语义的独立镜头中做多机位/多景别参考。"


def _reference_usage_role(frame: Dict[str, Any]) -> str:
    if not frame:
        return "original_planning"
    policy = str(frame.get("reference_use_policy") or "")
    if policy in {"evidence_only", "exclude"} or _reference_reuse_budget(frame) <= 0:
        return "evidence_only"
    tags = _frame_match_tags(frame)
    if _is_detail_reference(frame, tags):
        return "material_detail"
    if _is_spatial_reference(frame, tags):
        return "composition_light"
    if tags & {"process_action", "handshake", "signing", "document", "tablet"}:
        return "action_pose"
    if tags & {"establishing", "wide", "city", "office"}:
        return "composition_light"
    if tags & {"people_usage", "meeting", "team"}:
        return "scene_relation"
    if tags & {"transition_mood", "reflection", "silhouette", "copy_space"}:
        return "light_mood"
    if tags & {"outcome_emotion", "success", "applause"}:
        return "emotion_result"
    if policy == "style_only":
        return "style_only"
    if policy == "composition_only":
        return "composition_only"
    return "visual_reference"


def _is_spatial_reference(frame: Dict[str, Any], tags: set[str] | None = None) -> bool:
    frame_tags = tags or _frame_match_tags(frame)
    text = _search_text([
        frame.get("visual_summary"),
        frame.get("prompt_ready_brief"),
        frame.get("analysis_sections"),
        frame.get("subject_type"),
    ])
    has_space = bool(frame_tags & {"establishing", "wide", "city", "office", "silhouette", "copy_space"}) or any(
        keyword in text for keyword in ["楼宇", "建筑", "玻璃幕墙", "城市", "天际线", "大厅", "走廊", "空镜", "窗景", "会议室空间", "办公区", "倒影", "反射"]
    )
    action_dominant = any(keyword in text for keyword in ["握手", "签字", "签署", "笔尖", "手部局部", "双手", "钢笔落笔", "鼓掌"])
    return has_space and not action_dominant


def _is_detail_reference(frame: Dict[str, Any], tags: set[str] | None = None) -> bool:
    frame_tags = tags or _frame_match_tags(frame)
    if not frame_tags & {"detail_closeup", "closeup", "macro"}:
        return False
    text = _search_text([
        frame.get("visual_summary"),
        frame.get("prompt_ready_brief"),
        frame.get("analysis_sections"),
        frame.get("subject_type"),
    ])
    detail_keywords = ["微距", "极近", "局部", "手部", "笔尖", "钢笔", "指尖", "纸面", "袖口", "特写", "只截取", "裁切", "浅景深"]
    scene_keywords = ["宽幅", "远景", "中远景", "大厅", "团队", "多人围坐", "长桌两侧", "城市", "楼宇", "玻璃幕墙", "走廊", "高层会议室长桌"]
    if not any(keyword in text for keyword in detail_keywords):
        return False
    if frame_tags & {"wide", "establishing", "silhouette"}:
        return False
    return not any(keyword in text for keyword in scene_keywords)


def _reference_reuse_group(spec: Dict[str, Any], frame: Dict[str, Any] | None) -> str:
    if not frame:
        return ""
    frame_id = str(frame.get("frame_id") or "reference")
    return f"{_safe_id(frame_id)}::{_spec_primary_role(spec)}::{_safe_id(str(spec.get('scene_group') or spec.get('group') or 'scene'))}"


def _reference_compatible_with_spec(frame: Dict[str, Any], spec: Dict[str, Any]) -> bool:
    if _reference_semantic_conflict(frame, spec):
        return False
    if not _topic_semantic_required_match(frame, spec):
        return False
    role = _spec_primary_role(spec)
    usage_role = _reference_usage_role(frame)
    tags = _frame_match_tags(frame)
    if role in {"establishing", "end_copy_space", "transition_mood"} and tags & {"detail_closeup", "closeup", "macro"} and not tags & {"wide", "top_view"}:
        return False
    if usage_role in {"evidence_only", "style_only"}:
        return False
    if role == "establishing":
        return usage_role in {"composition_light", "light_mood", "visual_reference"}
    if role == "end_copy_space":
        return usage_role in {"composition_light", "light_mood", "visual_reference"}
    if role == "transition_mood":
        return usage_role in {"composition_light", "light_mood", "visual_reference"}
    if role == "detail_closeup":
        return usage_role in {"material_detail", "action_pose"}
    if role == "process_action":
        return usage_role in {"action_pose", "material_detail", "scene_relation"}
    if role == "people_usage":
        return usage_role in {"scene_relation", "action_pose", "composition_light"}
    if role == "outcome_emotion":
        return usage_role in {"action_pose", "emotion_result", "scene_relation"}
    if role == "main_subject":
        return usage_role in {"composition_light", "scene_relation", "visual_reference", "material_detail"}
    return True


def _reference_semantic_conflict(frame: Dict[str, Any], spec: Dict[str, Any]) -> bool:
    spec_text = _search_text([
        spec.get("subject"),
        spec.get("scene"),
        spec.get("action"),
        spec.get("group"),
    ])
    frame_text = _search_text([
        frame.get("visual_summary"),
        frame.get("prompt_ready_brief"),
        frame.get("analysis_sections"),
        frame.get("subject_type"),
        frame.get("scene_type"),
    ])
    if re.search(r"空会议室|空会议桌|空镜|整洁座位|桌面准备", spec_text):
        if re.search(r"握手|签字|签署|人物|商务人士|团队|对坐|行进|走在|参观|鼓掌", frame_text):
            return True
    if re.search(r"会议室|长桌|会议桌|签约桌", spec_text):
        if re.search(r"车间|工厂|产线|实验室通道|工业设备|制造车间", frame_text):
            return True
    if re.search(r"楼宇|幕墙|外景|天际线|建筑", spec_text):
        if re.search(r"签字|签署|手部|笔尖|合同纸面|会议桌前|室内会议", frame_text):
            return True
    if re.search(r"握手", spec_text):
        if re.search(r"鼓掌|祝贺|认可|团队成员.*坐|坐在会议桌旁", frame_text) and not re.search(r"握手|交握|双手紧握", frame_text):
            return True
        if re.search(r"签字|签署|笔尖|钢笔|合同纸面|多只手.*签署|签署空白合同|集体签约", frame_text) and not re.search(r"握手|鼓掌|达成|庆祝", frame_text):
            return True
    if re.search(r"鼓掌|祝贺|认可", spec_text):
        if re.search(r"握手|签字|签署|笔尖|钢笔|合同纸面", frame_text) and not re.search(r"鼓掌|祝贺|认可", frame_text):
            return True
    if re.search(r"签字|签署|笔尖|合同|文件", spec_text) and not re.search(r"空会议桌|空镜|桌面准备", spec_text):
        if re.search(r"楼宇外立面|城市天际线|大厅|走廊|空会议室", frame_text):
            return True
    return False


def _is_valid_multiview_reuse(spec: Dict[str, Any], selected_specs: Sequence[Dict[str, Any]]) -> bool:
    for selected in selected_specs:
        if _spec_scene_family(spec) != _spec_scene_family(selected):
            return False
        differences = 0
        for key in ["shot_role", "shot_type", "camera_angle", "motion", "group"]:
            if str(spec.get(key) or "") != str(selected.get(key) or ""):
                differences += 1
        if str(spec.get("composition") or "")[:28] != str(selected.get("composition") or "")[:28]:
            differences += 1
        if differences < 2:
            return False
    return True


def _spec_scene_family(spec: Dict[str, Any]) -> str:
    primary_text = _search_text([
        spec.get("title"),
        spec.get("subject"),
        spec.get("action"),
        spec.get("group"),
        spec.get("shot_role"),
    ])
    scene_text = _search_text([spec.get("scene")])
    all_text = f"{primary_text} {scene_text}".strip()
    family_text = re.sub(r"(?:非|不|不要|避免|不再).{0,8}握手", "", primary_text)
    if re.search(r"握手|交握|双手紧握", family_text):
        return "handshake"
    if re.search(r"鼓掌|祝贺|认可", family_text):
        return "applause"
    if re.search(r"平板|方案确认|窗边查看", family_text):
        return "tablet_discussion"
    if re.search(r"会议讨论|会议桌讨论|围绕会议桌|团队入座|合作站位|合影|洽谈|双方团队|负责人入座|团队关系", family_text):
        return "meeting_people"
    if re.search(r"签字|签署|笔尖|合同|纸面|文件夹|资料审阅|文件整理|签署资料|翻阅空白合同|桌面资料|文件递交|资料交接", family_text):
        return "document"
    if re.search(r"空会议室|空会议桌|空镜|桌面准备|会议室收束", family_text):
        return "empty_meeting_room"
    if re.search(r"楼宇|建筑|幕墙|外景|天际线|城市窗景|城市光线|玻璃反射|城市留白|窗景转场", family_text):
        return "building_city"
    if re.search(r"大厅|前台|走廊|入口|到访|进入会议|会议室入口", family_text):
        return "lobby_walkway"
    if re.search(r"办公区协作|开放办公|显示器|执行沟通|执行安排|工作区", family_text):
        return "office_work"
    if re.search(r"楼宇|建筑|幕墙|外景|天际线", scene_text) and not re.search(
        r"人物|团队|商务代表|负责人|签字|签署|握手|会议|讨论|平板|文件|合同|入座|鼓掌",
        all_text,
    ):
        return "building_city"
    if re.search(r"会议室|会议桌|长桌|座席", scene_text) and not re.search(r"签字|签署|笔尖|合同|文件", primary_text):
        return "meeting_people"
    return str(spec.get("shot_role") or "general")


def _assign_frames_to_specs(frames: Sequence[Dict[str, Any]], specs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any] | None]:
    if not frames:
        raise ValueError("没有可用参考帧。")
    usable_frames = [
        frame for frame in frames
        if str(frame.get("reference_use_policy") or "image2_reference") not in {"exclude", "evidence_only"}
        and float(frame.get("image2_usage_weight") or 0) > 0
    ] or list(frames)
    if not specs or str(specs[0].get("domain") or "") != "new_energy_vehicle":
        return _assign_frames_to_specs_frame_first(usable_frames, specs)
    assignments: List[Dict[str, Any] | None] = [None] * len(specs)
    group_sizes: Dict[str, int] = {}
    for spec in specs:
        group = str(spec.get("group") or "")
        group_sizes[group] = group_sizes.get(group, 0) + 1
    group_caps = {
        group: max(1, min(size, (size * 3 + 4) // 5))
        for group, size in group_sizes.items()
    }
    assigned_by_group: Dict[str, int] = {}
    selected_specs_by_frame: Dict[str, List[Dict[str, Any]]] = {}

    remaining_budget = {
        str(frame.get("frame_id") or ""): _reference_reuse_budget(frame)
        for frame in usable_frames
    }
    used_counts: Dict[str, int] = {}
    for index, spec in enumerate(specs):
        group = str(spec.get("group") or "")
        if assigned_by_group.get(group, 0) >= group_caps.get(group, len(specs)):
            continue
        selected = _best_frame_for_spec(
            spec,
            usable_frames,
            remaining_budget=remaining_budget,
            used_counts=used_counts,
            selected_specs_by_frame=selected_specs_by_frame,
            min_score=30,
        )
        if selected is None:
            continue
        frame_id = str(selected.get("frame_id") or "")
        assignments[index] = selected
        remaining_budget[frame_id] = max(0, remaining_budget.get(frame_id, 0) - 1)
        used_counts[frame_id] = used_counts.get(frame_id, 0) + 1
        selected_specs_by_frame.setdefault(frame_id, []).append(spec)
        assigned_by_group[group] = assigned_by_group.get(group, 0) + 1

    return assignments


def _assign_frames_to_specs_frame_first(frames: Sequence[Dict[str, Any]], specs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any] | None]:
    assignments: List[Dict[str, Any] | None] = [None] * len(specs)
    group_sizes: Dict[str, int] = {}
    for spec in specs:
        group = str(spec.get("group") or "")
        group_sizes[group] = group_sizes.get(group, 0) + 1
    group_caps = {
        group: max(1, min(size, (size * 3 + 4) // 5))
        for group, size in group_sizes.items()
    }
    assigned_by_group: Dict[str, int] = {}
    selected_specs_by_frame: Dict[str, List[Dict[str, Any]]] = {}

    for frame in frames:
        frame_id = str(frame.get("frame_id") or "")
        reuse_budget = _reference_reuse_budget(frame)
        if reuse_budget <= 0:
            continue
        selected_specs_by_frame.setdefault(frame_id, [])
        for _ in range(reuse_budget):
            target_index = _best_unassigned_spec_index(
                frame,
                specs,
                assignments,
                assigned_by_group=assigned_by_group,
                group_caps=group_caps,
                selected_specs_for_frame=selected_specs_by_frame[frame_id],
                min_score=20 if selected_specs_by_frame[frame_id] else 30,
            )
            if target_index is None:
                break
            assignments[target_index] = frame
            selected_spec = specs[target_index]
            selected_specs_by_frame[frame_id].append(selected_spec)
            group = str(selected_spec.get("group") or "")
            assigned_by_group[group] = assigned_by_group.get(group, 0) + 1

    return assignments


def _best_frame_for_spec(
    spec: Dict[str, Any],
    frames: Sequence[Dict[str, Any]],
    remaining_budget: Dict[str, int],
    used_counts: Dict[str, int],
    selected_specs_by_frame: Dict[str, List[Dict[str, Any]]],
    min_score: int = 1,
) -> Dict[str, Any] | None:
    preferred = set(spec.get("preferred_categories") or [])
    best_frame: Dict[str, Any] | None = None
    best_score = -1
    for frame in frames:
        frame_id = str(frame.get("frame_id") or "")
        if remaining_budget.get(frame_id, 0) <= 0:
            continue
        selected_specs = selected_specs_by_frame.get(frame_id, [])
        if not _reference_compatible_with_spec(frame, spec):
            continue
        if selected_specs and not _is_valid_multiview_reuse(spec, selected_specs):
            continue
        frame_tags = _frame_match_tags(frame)
        score = _frame_role_score(frame, spec, frame_tags)
        score += len(frame_tags & preferred) * 3
        score += int(float(frame.get("topic_fit_score") or 50) / 20)
        score += int(float(frame.get("image2_usage_weight") or 0.5) * 10)
        score += _topic_semantic_binding_score(frame, spec)
        score -= used_counts.get(frame_id, 0) * 8
        if selected_specs:
            group = str(spec.get("group") or "")
            same_group_count = sum(1 for selected in selected_specs if str(selected.get("group") or "") == group)
            same_role_count = sum(
                1
                for selected in selected_specs
                if _spec_primary_role(selected) == _spec_primary_role(spec)
            )
            score -= same_group_count * 28
            score -= same_role_count * 12
        if score > best_score:
            best_score = score
            best_frame = frame
    return best_frame if best_score >= min_score else None


def _topic_semantic_required_match(frame: Dict[str, Any], spec: Dict[str, Any]) -> bool:
    spec_text = _search_text([spec.get("title"), spec.get("subject"), spec.get("action"), spec.get("scene")])
    frame_text = _search_text([
        frame.get("visual_summary"),
        frame.get("subject_type"),
        frame.get("scene_type"),
        frame.get("prompt_ready_brief"),
        frame.get("commercial_use_cases"),
    ])
    required_groups = [
        (["充电", "补能", "快充", "充电站", "充电桩", "桩位"], ["充电", "补能", "快充", "充电站", "充电桩", "桩位", "充电口", "充电枪"]),
        (["动力电池", "电芯", "电池包", "电驱", "底盘"], ["电池", "电芯", "电池包", "电驱", "底盘", "透明车身", "动力系统"]),
        (["工厂", "产线", "机械臂", "制造", "装配", "下线"], ["工厂", "产线", "机械臂", "制造", "装配", "车身框架", "检测"]),
        (["工程师", "研发", "运维", "科研", "调试"], ["工程师", "研发", "运维", "科研", "实验室", "调试", "沙盘"]),
        (["氢", "风机", "光伏", "绿色能源", "清洁能源", "能源场", "双碳"], ["氢", "风机", "光伏", "绿色能源", "清洁能源", "能源场", "双碳", "风电"]),
        (["自动驾驶", "智能驾驶", "智驾", "车路协同", "HUD", "泊车", "跟车", "感知", "车道", "路口"], ["自动驾驶", "智能驾驶", "智驾", "车路协同", "HUD", "泊车", "跟车", "感知", "车道", "路口", "道路", "路径", "驾驶辅助"]),
    ]
    for spec_keywords, frame_keywords in required_groups:
        if any(keyword in spec_text for keyword in spec_keywords) and not any(keyword in frame_text for keyword in frame_keywords):
            return False
    return True


def _topic_semantic_binding_score(frame: Dict[str, Any], spec: Dict[str, Any]) -> int:
    spec_text = _search_text([spec.get("title"), spec.get("subject"), spec.get("action"), spec.get("scene")])
    frame_text = _search_text([
        frame.get("visual_summary"),
        frame.get("subject_type"),
        frame.get("scene_type"),
        frame.get("prompt_ready_brief"),
        frame.get("composition_tags"),
        frame.get("commercial_use_cases"),
    ])
    keyword_groups = [
        (["充电", "补能", "充电桩", "快充", "充电站", "桩位"], 34),
        (["电池", "电芯", "电驱", "底盘", "透明车身", "透明电驱", "动力系统"], 34),
        (["工厂", "产线", "机械臂", "制造", "装配", "车身框架", "检测"], 34),
        (["自动驾驶", "智能驾驶", "智驾", "车路协同", "HUD", "泊车", "跟车", "感知", "车道", "路口"], 34),
        (["风机", "光伏", "氢", "氢能", "绿色能源", "清洁能源", "能源场", "双碳"], 26),
        (["工程师", "研发", "运维", "沙盘", "科研", "实验室", "调试"], 30),
        (["城市道路", "智慧道路", "高架", "桥梁", "车流", "天际线"], 22),
    ]
    score = 0
    for keywords, weight in keyword_groups:
        spec_hit = any(keyword in spec_text for keyword in keywords)
        frame_hit = any(keyword in frame_text for keyword in keywords)
        if spec_hit and frame_hit:
            score += weight
        elif spec_hit and not frame_hit:
            score -= weight
    return score


def _best_unassigned_spec_index(
    frame: Dict[str, Any],
    specs: Sequence[Dict[str, Any]],
    assignments: Sequence[Dict[str, Any] | None],
    assigned_by_group: Dict[str, int] | None = None,
    group_caps: Dict[str, int] | None = None,
    selected_specs_for_frame: Sequence[Dict[str, Any]] | None = None,
    min_score: int = 1,
) -> int | None:
    best_index: int | None = None
    best_score = -1
    frame_tags = _frame_match_tags(frame)
    for index, spec in enumerate(specs):
        if assignments[index] is not None:
            continue
        group = str(spec.get("group") or "")
        if group_caps and assigned_by_group and assigned_by_group.get(group, 0) >= group_caps.get(group, len(specs)):
            continue
        if not _reference_compatible_with_spec(frame, spec):
            continue
        if selected_specs_for_frame and not _is_valid_multiview_reuse(spec, selected_specs_for_frame):
            continue
        score = _frame_role_score(frame, spec, frame_tags)
        if selected_specs_for_frame:
            same_group_count = sum(1 for selected in selected_specs_for_frame if str(selected.get("group") or "") == group)
            same_role_count = sum(
                1
                for selected in selected_specs_for_frame
                if _spec_primary_role(selected) == _spec_primary_role(spec)
            )
            score -= same_group_count * 28
            score -= same_role_count * 12
        if score > best_score:
            best_index = index
            best_score = score
    return best_index if best_score >= min_score else None


def _pick_frame_for_spec(
    frames: Sequence[Dict[str, Any]],
    spec: Dict[str, Any],
    reuse: Dict[str, int],
) -> Dict[str, Any]:
    preferred = set(spec.get("preferred_categories") or [])
    scored = []
    for frame in frames:
        frame_id = str(frame.get("frame_id") or "")
        frame_tags = _frame_match_tags(frame)
        score = _frame_role_score(frame, spec, frame_tags)
        score += len(frame_tags & preferred) * 3
        score += int(float(frame.get("topic_fit_score") or 50) / 20)
        score += int(float(frame.get("image2_usage_weight") or 0.5) * 10)
        score -= reuse.get(frame_id, 0) * 8
        scored.append((score, frame_id, frame))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = scored[0][2]
    selected_id = str(selected.get("frame_id") or "")
    reuse[selected_id] = reuse.get(selected_id, 0) + 1
    return selected


def _frame_match_tags(frame: Dict[str, Any]) -> set[str]:
    tags = set(_as_list(frame.get("categories")))
    tags.update(_as_list(frame.get("shot_role_tags")))
    tags.update(_as_list(frame.get("composition_tags")))
    if frame.get("subject_type"):
        tags.add(str(frame["subject_type"]))
    if frame.get("scene_type"):
        tags.add(str(frame["scene_type"]))
    return tags


def _frame_role_score(frame: Dict[str, Any], spec: Dict[str, Any], frame_tags: set[str] | None = None) -> int:
    tags = frame_tags or _frame_match_tags(frame)
    role = _spec_primary_role(spec)
    text = _search_text([frame.get("analysis_sections"), frame.get("analysis_prompt"), frame.get("prompt_ready_brief")])
    has_detail = bool(tags & {"detail_closeup", "closeup", "macro", "signing", "document"}) or any(
        keyword in text for keyword in ["微距", "特写", "近景", "极近", "手部", "笔尖", "钢笔", "签字"]
    )
    strong_space_tags = tags & {"establishing", "wide", "city", "office", "silhouette"}
    has_copy_space = "copy_space" in tags and not has_detail
    has_space = bool(strong_space_tags) or has_copy_space or any(
        keyword in text for keyword in ["远景", "中远景", "宽幅", "全景", "空镜", "城市", "楼宇", "建筑", "玻璃幕墙", "会议室空间", "办公室空间", "窗景", "倒影"]
    )
    if has_detail and not strong_space_tags:
        has_space = False
    has_people_action = bool(tags & {"people_usage", "process_action", "handshake", "meeting", "team", "applause", "success"}) or any(
        keyword in text for keyword in ["人物", "团队", "握手", "会议", "讨论", "鼓掌", "见证", "达成", "合作"]
    )

    score = 0
    if role == "establishing":
        score += 35 if has_space else 0
        score += 14 if tags & {"wide", "city", "office", "silhouette"} else 0
        score -= 28 if has_people_action and not tags & {"establishing", "city", "office", "copy_space", "silhouette"} else 0
        score -= 80 if has_detail and not has_space else 0
    elif role == "end_copy_space":
        score += 28 if has_space else 0
        score += 20 if tags & {"copy_space", "wide", "silhouette"} and not has_detail else 0
        score -= 24 if has_people_action and not tags & {"copy_space", "silhouette"} else 0
        score -= 65 if has_detail else 0
    elif role == "transition_mood":
        score += 24 if tags & {"transition_mood", "reflection", "silhouette", "depth", "copy_space"} else 0
        score += 10 if has_space else 0
        score -= 14 if has_people_action and not tags & {"transition_mood", "reflection", "silhouette"} else 0
        score -= 16 if has_detail and "reflection" not in tags else 0
    elif role == "detail_closeup":
        score += 44 if has_detail else 0
        score += 24 if tags & {"closeup", "macro", "detail_closeup"} else 0
        score -= 18 if has_space and not has_detail else 0
    elif role == "process_action":
        score += 34 if tags & {"process_action", "handshake", "signing", "document", "tablet"} or has_people_action else 0
        score += 8 if has_detail else 0
    elif role == "people_usage":
        score += 34 if tags & {"people_usage", "meeting", "team"} or has_people_action else 0
        score += 10 if has_people_action and has_space else 0
        score -= 18 if has_detail and not has_people_action else 0
    elif role == "outcome_emotion":
        score += 34 if tags & {"outcome_emotion", "success", "applause", "handshake"} or any(keyword in text for keyword in ["成功", "达成", "庆祝", "鼓掌"]) else 0
        score -= 16 if has_detail and not has_people_action else 0
    else:
        score += 16 if tags & {"main_subject", "medium", "wide"} else 0
        score += 8 if has_space or has_people_action else 0
    return score


def _storyboard_lane_for_assignment(frame: Dict[str, Any] | None, frame_usage_index: int) -> str:
    if not frame:
        return "main"
    if frame_usage_index <= 0:
        return "main"
    if _reference_reuse_budget(frame) <= 1:
        return "main"
    if _reference_usage_role(frame) in {"evidence_only", "style_only"}:
        return "main"
    return "extension"


def _compose_image_prompt(
    spec: Dict[str, Any],
    frame: Dict[str, Any] | None,
    global_style: str,
    negative_prompt: str,
    storyboard_lane: str = "main",
    reference_role: str = "standalone",
    anchor_shot_id: str | None = None,
) -> str:
    reference_usage = _reference_usage_for_shot(frame, spec, storyboard_lane, reference_role=reference_role, anchor_shot_id=anchor_shot_id)
    negative = _strip_negative_prefix(_compose_negative_prompt(frame, negative_prompt))
    secondary = "、".join(str(item) for item in spec.get("secondary", []) if str(item).strip())
    role = _spec_primary_role(spec)
    supporting = _prompt_supporting_elements(spec, role, secondary)
    image_body = _image_director_body(spec, role, supporting, storyboard_lane)
    style = (
        f"{spec['lighting']}，{spec['color']}，{spec['mood']}。"
        f"{global_style}"
    )
    lines = [
        "生成图片：",
        image_body,
        f"参考图使用：{reference_usage}",
        f"整体质感：{style}",
        f"不要出现：{negative}",
    ]
    return "\n".join(line for line in lines if line)


def _prompt_supporting_elements(spec: Dict[str, Any], role: str, fallback: str) -> str:
    corpus = _primary_story_text(spec)
    if _is_new_energy_vehicle_story(spec, corpus):
        return _nev_supporting_elements(corpus, role, fallback)
    if re.search(r"楼宇|大楼|建筑|玻璃幕墙|天际线|高层|外立面", corpus):
        return "天空云层、玻璃反射、城市轮廓、建筑线条和环境光影"
    if re.search(r"空会议室|空会议桌|空镜|整洁座位|桌面准备", corpus):
        return "整齐座椅、桌面边缘、玻璃隔断、窗光反射和干净留白"
    if re.search(r"签字|签署|笔尖|纸面|合同|文件", corpus) and role == "detail_closeup":
        return "纸面纹理、笔尖接触、袖口边缘、手部姿态和浅景深背景"
    if re.search(r"握手", corpus):
        return "西装袖口、握手手部、会议桌边缘、背景团队和窗边光线"
    if re.search(r"鼓掌|祝贺|认可", corpus):
        return "鼓掌手部、人物层次、会议桌前景、窗边光线和背景虚化"
    if role in {"establishing", "transition_mood", "end_copy_space"}:
        return "留白区域、环境层次、光影变化、前景遮挡和空间纵深"
    return fallback or "必要的环境层次、真实道具和前后景关系"


def _image_director_body(spec: Dict[str, Any], role: str, supporting: str, storyboard_lane: str) -> str:
    subject = str(spec.get("subject") or "").strip()
    scene = str(spec.get("scene") or "").strip()
    action = str(spec.get("action") or "").strip()
    composition = str(spec.get("composition") or "").strip()
    shot_type = str(spec.get("shot_type") or "").strip()
    camera_angle = str(spec.get("camera_angle") or "").strip()
    extension_note = (
        "这是一张同场景延展画面，需要换机位、换景别或换动作阶段，避免和锚点主画面同构图。"
        if storyboard_lane == "extension"
        else ""
    )
    camera = f"{composition}，{shot_type}，{camera_angle}".strip("，")
    if role == "detail_closeup":
        body = (
            f"{subject}的局部特写，场景位于{scene}。{action}，画面焦点集中在材质、边缘、手部或道具接触关系上，"
            f"{supporting}只作为弱化背景层次。{camera}，浅景深，纹理真实清楚，画面干净克制。"
        )
    elif role in {"establishing", "transition_mood", "end_copy_space"}:
        body = (
            f"{subject}，场景为{scene}。{action}。画面以空间、建筑线条、窗光、反射、留白和环境层次为主，"
            f"{supporting}保持简洁，不让人物动作抢占画面。{camera}，前景、中景、背景关系清楚，画面安静完整，留白干净。"
        )
    elif role in {"process_action", "people_usage", "outcome_emotion"}:
        is_nev_story = _is_new_energy_vehicle_story(spec, _primary_story_text(spec))
        relation_phrase = (
            _nev_image_relation_phrase(spec, role)
            if is_nev_story
            else "人物、手部、桌面道具和空间背景之间的关系要真实可读"
        )
        action_quality = (
            "运动状态或操作阶段停在清楚可读的一刻，主体结构和空间关系稳定，不夸张摆拍"
            if is_nev_story
            else "动作停在清楚可读的一刻，表情和姿态克制，不夸张摆拍"
        )
        body = (
            f"{subject}，发生在{scene}。{action}。{relation_phrase}，"
            f"{supporting}自然融入画面。{camera}，{action_quality}。"
        )
    else:
        body = (
            f"{subject}，位于{scene}。{action}。{supporting}共同构成完整画面。"
            f"{camera}，主体位置、留白方向、透视关系和光线层次明确。"
        )
    return f"{body}{extension_note}".strip()


def _spec_primary_role(spec: Dict[str, Any]) -> str:
    if spec.get("shot_role") in SHOT_ROLE_SET:
        return str(spec["shot_role"])
    for item in spec.get("preferred_categories") or []:
        if item in SHOT_ROLE_SET:
            return str(item)
    return "main_subject"


def _compose_video_prompt(spec: Dict[str, Any], frame: Dict[str, Any] | None) -> str:
    sections = frame.get("analysis_sections", {}) if frame else {}
    spec_corpus = " ".join(
        str(value or "")
        for value in [
            spec.get("title"),
            spec.get("subject"),
            spec.get("action"),
            spec.get("scene"),
            spec.get("shot_type"),
            spec.get("composition"),
            spec.get("lighting"),
            spec.get("motion"),
            spec.get("group"),
            spec.get("purpose"),
            spec.get("domain"),
        ]
    )
    full_corpus = " ".join(
        str(value or "")
        for value in [
            spec_corpus,
            sections.get("构图"),
            sections.get("视角/镜头"),
            sections.get("光线"),
            sections.get("色彩"),
            sections.get("材质与细节"),
            frame.get("prompt_ready_brief") if frame else "",
        ]
    )
    role = _spec_primary_role(spec)
    anchor = _video_current_frame_anchor(spec, full_corpus)
    camera_move = _infer_video_camera_move(spec, full_corpus)
    subject_motion = _infer_video_subject_motion(spec, full_corpus)
    scene_motion = _infer_video_scene_motion(spec, full_corpus)
    keep_style = _video_stability_rule(role, spec)
    negative = (
        "文字、Logo、水印、真实品牌名、真实公司名、可读小字、乱码、跳帧、主体漂移、"
        "肢体或结构变形、重复主体、夸张动作、画面闪烁、过度锐化或过度磨皮"
    )
    return (
        f"从当前画面开始，{anchor}。{camera_move}；{subject_motion}；{scene_motion}。"
        f"{keep_style}。不要出现：{negative}。"
    )


def _video_domain_style(domain: str) -> str:
    return {
        "new_energy_vehicle": "新能源汽车科技宣传片级真实视频质感",
        "business": "企业宣传片级真实视频质感",
        "festival": "商业广告级真实视频质感",
        "industrial": "工业企业宣传片级真实视频质感",
        "lab": "科研宣传片级真实视频质感",
        "product": "商业产品广告级真实视频质感",
        "medical": "医疗健康宣传片级真实视频质感",
        "education": "教育宣传片级真实视频质感",
        "tourism": "文旅宣传片级真实视频质感",
    }.get(domain, "商业素材级真实视频质感")


def _clean_video_action_focus(value: str) -> str:
    text = re.sub(r"(镜头时长|持续时间|视频时长|时长)\s*[：:]?\s*\d+(?:\.\d+)?\s*秒[。；;，,\s]*", "", value)
    text = re.sub(r"只表现一个清楚的[^：:。；;]+[：:]\s*", "", text)
    text = re.sub(r"人物动作自然克制|西装和文件细节保持稳定|镜头运动平滑", "", text)
    return re.sub(r"[。；;，,\s]+$", "", text.strip())


def _pick_variant(options: Sequence[str], seed: Any) -> str:
    if not options:
        return ""
    seed_text = str(seed or "")
    index = sum(ord(char) for char in seed_text) % len(options)
    return options[index]


def _primary_story_text(spec: Dict[str, Any]) -> str:
    return " ".join(
        str(spec.get(key) or "")
        for key in ["group", "title", "subject", "action", "shot_type", "composition", "scene", "domain"]
    )


def _story_location_text(spec: Dict[str, Any]) -> str:
    return " ".join(str(spec.get(key) or "") for key in ["group", "title", "subject", "scene"])


NEV_STORY_PATTERN = r"新能源汽车|新能源车|电动车|电动汽车|智能驾驶|自动驾驶|智驾|车路协同|车联网|智能座舱|充电桩|充电站|充电口|充电枪|换电|动力电池|汽车电池|电芯|电池包|电驱|电机|HUD|车道|前车|巡航|泊车|汽车工厂|车身|低碳|绿色出行|氢燃料"
BUSINESS_MOTION_PATTERN = r"商务人士|会议区域|会议室|会议桌|会议|手持文件|文件|合同|签字|签署|握手|鼓掌|西装|桌面资料|桌面道具"


def _is_new_energy_vehicle_story(spec: Dict[str, Any], corpus: str = "") -> bool:
    domain = str(spec.get("domain") or "")
    return domain == "new_energy_vehicle" or bool(re.search(NEV_STORY_PATTERN, corpus))


def _nev_story_kind(corpus: str) -> str:
    if re.search(r"充电|补能|快充|桩位|充电口|充电枪|线缆|换电", corpus):
        return "charging"
    if re.search(r"电池|电芯|电池包|模组|底盘|电驱|电机|固态", corpus):
        return "battery"
    if re.search(r"产线|工厂|车间|机械臂|装配|焊接|检测|下线|制造", corpus):
        return "factory"
    if re.search(r"工程师|研发|实验室|控制室|运维|调试|透明屏|平板", corpus):
        return "engineer"
    if re.search(r"风机|光伏|太阳能|储能|氢|能源场|零排放|低碳", corpus):
        return "energy"
    if re.search(r"自动驾驶|智能驾驶|智驾|车路协同|车道|前车|巡航|HUD|泊车|道路|高架|高速", corpus):
        return "road"
    return "vehicle"


def _nev_supporting_elements(corpus: str, role: str, fallback: str) -> str:
    kind = _nev_story_kind(corpus)
    if kind == "road":
        return "车道线、前车距离、感知光效、道路护栏、城市天际线和车内 HUD 层次"
    if kind == "charging":
        return "车辆充电口、充电枪、线缆弧度、桩位秩序、地面反光和场站空间"
    if kind == "battery":
        return "电池包结构、电芯排列、金属边缘、冷白工业光和洁净检测台面"
    if kind == "factory":
        return "车身骨架、机械臂、输送线、检测工位、工业灯带和洁净通道"
    if kind == "engineer":
        return "工程师姿态、抽象车辆数据界面、设备边缘、实验室光线和操作空间"
    if kind == "energy":
        return "车辆、风机、光伏板、储能设备、清洁天空和绿色能源光效"
    if role in {"establishing", "transition_mood", "end_copy_space"}:
        return "道路纵深、场站留白、能源设施、城市背景和柔和反射层次"
    return fallback or "车辆主体、道路或场站环境、能源设备和前后景关系"


def _nev_image_relation_phrase(spec: Dict[str, Any], role: str) -> str:
    corpus = _primary_story_text(spec)
    kind = _nev_story_kind(corpus)
    if kind == "road":
        return "车辆、车道线、前车距离、感知光效和道路背景之间的关系要真实可读"
    if kind == "charging":
        return "车辆、充电枪、线缆、充电桩和场站背景之间的关系要真实可读"
    if kind == "battery":
        return "电池结构、电芯排列、检测设备和工业空间之间的关系要真实可读"
    if kind == "factory":
        return "车身、机械臂、输送线、检测工位和车间空间之间的关系要真实可读"
    if kind == "engineer":
        return "工程师、设备、抽象数据界面和研发空间之间的关系要真实可读"
    if kind == "energy":
        return "车辆、能源设施、道路或场站环境之间的关系要真实可读"
    return "车辆主体、关键设备、空间背景和前后景关系要真实可读"


def _video_current_frame_anchor(spec: Dict[str, Any], corpus: str) -> str:
    subject = str(spec.get("subject") or "").strip()
    if _is_new_energy_vehicle_story(spec, corpus):
        kind = _nev_story_kind(corpus)
        if kind == "road":
            return "保持当前新能源车、车道线、前车距离和道路纵深透视"
        if kind == "charging":
            return f"保持当前{subject or '充电场景'}的车辆、充电枪、线缆和桩位关系"
        if kind == "battery":
            return f"保持当前{subject or '动力电池结构'}的电芯排列、金属边缘和空间层次"
        if kind == "factory":
            return f"保持当前{subject or '汽车工厂产线'}的车身、机械臂和产线纵深"
        if kind == "engineer":
            return f"保持当前{subject or '工程调试场景'}的人物、设备和抽象车辆数据界面关系"
        if kind == "energy":
            return f"保持当前{subject or '绿色能源出行画面'}的车辆、能源设施和环境层次"
        return f"保持当前{subject or '新能源汽车主体'}的外观、空间位置和科技质感"
    if re.search(r"楼宇|大楼|建筑|玻璃幕墙|天际线|高层|外立面", corpus):
        return f"保持当前{subject or '商务楼宇'}的建筑构图和玻璃幕墙线条"
    if re.search(r"空会议室|空会议桌|空镜|整洁座位|桌面准备", corpus):
        return f"保持当前{subject or '空会议室'}的安静空间关系"
    if re.search(r"鼓掌|祝贺|认可", corpus):
        return f"保持当前{subject or '团队认可'}的人物层次和鼓掌动作关系"
    if re.search(r"握手", corpus):
        return f"保持当前{subject or '合作握手'}的人物站位和手部关系"
    if re.search(r"达成|成功|合影|阵列", corpus):
        return f"保持当前{subject or '合作达成'}的人物站位和空间关系"
    if re.search(r"签字|签署|笔尖|纸面|合同|文件", corpus):
        return f"保持当前{subject or '签署细节'}的桌面和手部构图"
    if re.search(r"走廊|大厅|前台|入场|进入|门口", corpus):
        return f"保持当前{subject or '商务入场空间'}的纵深透视"
    return f"保持当前{subject or '主体'}的构图、光线和空间位置"


def _infer_nev_video_camera_move(spec: Dict[str, Any], corpus: str, role: str, seed: Any, motion: str) -> str:
    kind = _nev_story_kind(corpus)
    if kind == "road":
        return _pick_variant(
            [
                "平视中景沿道路纵深缓慢推进，车道线和前车距离保持稳定",
                "车内驾驶视角轻微后退或稳定前推，让 HUD 感知层和道路透视产生细微视差",
                "稳定跟随车辆行驶方向轻微侧移，保持车身、车道线和前车关系清楚",
            ],
            seed,
        )
    if kind == "charging":
        return _pick_variant(
            [
                "中近景沿车辆侧后方缓慢推近，充电枪、线缆和桩位关系保持清晰",
                "固定机位配合轻微横移，让充电桩阵列和地面反光产生细微视差",
                "近景缓慢拉近充电接口，保持车身漆面、线缆弧度和指示灯稳定",
            ],
            seed,
        )
    if kind == "battery":
        return _pick_variant(
            [
                "近景沿电芯排列方向缓慢滑动，金属边缘和冷白工业光保持稳定",
                "固定微距配合轻微焦点转移，让电池模组层次自然显现",
                "中近景缓慢推近电池包结构，保持排列秩序和材质纹理清楚",
            ],
            seed,
        )
    if kind == "factory":
        return _pick_variant(
            [
                "稳定横移经过产线前景，车身骨架和机械臂形成清楚纵深",
                "中景缓慢推入装配工位，保持机械臂轨迹和车身位置稳定",
                "固定工业机位轻微侧移，让输送线和工位灯带产生克制视差",
            ],
            seed,
        )
    if kind == "engineer":
        return _pick_variant(
            [
                "平视中景缓慢推近工程师和设备，抽象数据界面保持不可读且稳定",
                "稳定侧移经过控制台前景，人物姿态、设备边缘和空间透视保持一致",
                "中近景轻微拉近操作区域，保留研发空间和车辆模型的层次",
            ],
            seed,
        )
    if kind == "energy":
        return _pick_variant(
            [
                "宽幅远景缓慢横移，让车辆、风机、光伏和道路形成稳定绿色能源层次",
                "轻微上升或后退拉开能源设施与出行场景的空间关系",
                "稳定中远景缓慢推进，保持清洁天空、能源设备和车辆位置清楚",
            ],
            seed,
        )
    if motion and motion not in {"轻微横移", "缓慢推近", "轻微推近"}:
        return f"{motion}，车辆或设备主体保持在画面中心，运动幅度克制稳定"
    return "稳定机位配合轻微推近或横移，保持车辆主体、科技光效和空间层次清楚"


def _infer_nev_video_subject_motion(spec: Dict[str, Any], corpus: str) -> str:
    kind = _nev_story_kind(corpus)
    if kind == "road":
        return "新能源车沿车道平稳前行，前车距离、车道保持和感知光效只做细微连续变化"
    if kind == "charging":
        return "充电枪、线缆和车身接口保持稳定，能量光效或指示灯轻微流动，不新增无关人物"
    if kind == "battery":
        return "电池模组、电芯或透明结构保持稳定，只出现轻微光效扫描和材质高光变化"
    if kind == "factory":
        return "机械臂或输送线做小幅真实运行，车身和工位关系保持一致，不改变结构"
    if kind == "engineer":
        return "工程师只做小幅查看、指向或调试动作，设备和抽象界面保持稳定不可读"
    if kind == "energy":
        return "车辆或能源设备保持平稳，风机、光伏反光或能量光效缓慢变化"
    action = _clean_video_action_focus(str(spec.get("action") or spec.get("subject") or ""))
    return action or "车辆或设备主体只做清楚、克制、连续的真实运动"


def _infer_nev_video_scene_motion(spec: Dict[str, Any], corpus: str) -> str:
    kind = _nev_story_kind(corpus)
    if kind == "road":
        return "道路护栏、车道线、城市背景和玻璃反射产生轻微视差，空间透视保持稳定"
    if kind == "charging":
        return "充电站灯带、地面反光、桩位阵列和远处车辆只做轻微环境变化"
    if kind == "battery":
        return "冷白工业灯、金属反射和浅景深背景轻微变化，电芯排列不跳变"
    if kind == "factory":
        return "工位灯带、机械臂阴影和产线背景轻微变化，车身结构不漂移"
    if kind == "engineer":
        return "实验室或控制室光线、屏幕光和设备反射轻微变化，空间位置保持一致"
    if kind == "energy":
        return "天空、风机、光伏反射和远处道路缓慢变化，整体环境保持清洁稳定"
    return "背景维持轻微环境动态和真实光影变化，不改变车辆、设备和空间位置"


def _nev_video_stability_rule(role: str, spec: Dict[str, Any]) -> str:
    corpus = _primary_story_text(spec)
    kind = _nev_story_kind(corpus)
    base = "整体保持新能源汽车科技宣传片级真实视频质感，低饱和色调和柔和自然光稳定，镜头运动平滑"
    if kind == "road":
        return f"{base}，车辆外观、车道线、前车距离、HUD 感知层和道路透视保持一致"
    if kind == "charging":
        return f"{base}，车辆、充电枪、线缆、充电桩和场站位置保持一致"
    if kind == "battery":
        return f"{base}，电芯排列、金属结构、接口边缘和光效位置保持一致"
    if kind == "factory":
        return f"{base}，机械臂、车身结构、产线工位和工业空间位置保持一致"
    if kind == "engineer":
        return f"{base}，人物身份、工装、手部结构、设备边缘和空间位置保持一致"
    if kind == "energy":
        return f"{base}，车辆、能源设施、道路和清洁天空的空间关系保持一致"
    return f"{base}，车辆主体、设备材质、空间位置和构图关系保持一致"


def _infer_video_camera_move(spec: Dict[str, Any], corpus: str) -> str:
    seed = spec.get("title") or spec.get("action")
    role = _spec_primary_role(spec)
    motion = str(spec.get("motion") or "").strip()
    if _is_new_energy_vehicle_story(spec, corpus):
        return _infer_nev_video_camera_move(spec, corpus, role, seed, motion)
    if re.search(r"飞机|航班|天空", corpus) and re.search(r"楼宇|玻璃幕墙|建筑", corpus):
        return "镜头沿建筑立面缓慢上仰并轻微推进，天空留白保持稳定"
    if re.search(r"楼宇|大楼|建筑|玻璃幕墙|天际线|高层|外立面", corpus):
        return _pick_variant(
            [
                "宽幅远景缓慢推近，玻璃幕墙和城市反射产生轻微视差",
                "镜头沿建筑立面做稳定上仰滑动，突出高层线条和天空留白",
                "固定低角度机位轻微右移，保留建筑垂直线和玻璃反射层次",
            ],
            seed,
        )
    if re.search(r"空会议室|空会议桌|空镜|整洁座位|桌面准备", corpus):
        return "固定机位轻微向前推进，沿会议桌方向产生很小的空间视差"
    if re.search(r"鼓掌|祝贺|认可", corpus):
        return _pick_variant(
            [
                "平视中景轻微推近，让鼓掌人物形成前后层次，桌面文件保持在前景",
                "稳定机位小幅侧移，保留团队成员克制鼓掌和窗边背景层次",
                "中景缓慢拉近，重点保持手部鼓掌动作清楚、人物表情自然",
            ],
            seed,
        )
    if re.search(r"握手", corpus):
        return _pick_variant(
            [
                "中近景稳定微推，镜头在握手或确认动作完成后轻微停稳",
                "平视近景做小幅横向滑动，让手部、西装袖口和背景团队形成层次",
                "长焦浅景深轻微拉近，保持手部清晰，背景人物只做弱虚化运动",
            ],
            seed,
        )
    if re.search(r"达成|成功|合影|阵列", corpus):
        return _pick_variant(
            [
                "宽幅中景缓慢推近，保持团队阵列和桌面文件关系稳定",
                "平视机位轻微后退，拉开成功达成后的空间层次和留白",
                "稳定横移经过前景桌面，让团队站位和窗光形成正式收束感",
            ],
            seed,
        )
    if re.search(r"签字|签署|笔尖|纸面|合同|文件", corpus) or role == "detail_closeup":
        return _pick_variant(
            [
                "近景贴着桌面稳定微推，焦点从纸面纹理自然落到笔尖或手部动作",
                "低角度桌面近景缓慢侧移，沿文件边缘掠过并保持手部清晰",
                "固定近景配合轻微焦点转移，让纸张、笔尖和袖口层次自然显现",
            ],
            seed,
        )
    if re.search(r"会议|讨论|团队|方案|平板|资料", corpus) or role == "people_usage":
        return _pick_variant(
            [
                "镜头沿会议桌边缘缓慢侧移，保持主要人物和桌面资料在画面中心",
                "平视中景缓慢推近，焦点从前景文件过渡到正在交流的人物",
                "稳定机位轻微拉近，让翻页、点头和手势自然发生",
            ],
            seed,
        )
    if re.search(r"走廊|大厅|前台|入场|进入|门口", corpus):
        return _pick_variant(
            [
                "镜头沿走廊纵深稳定向前推进，玻璃隔断产生轻微反射变化",
                "平视中景缓慢后退，让商务人士自然进入画面并靠近会议区域",
                "侧后方轻微跟拍人物前行，保持步伐稳定和空间透视线",
            ],
            seed,
        )
    if role == "transition_mood":
        return _pick_variant(
            [
                "半空镜缓慢横移，让窗光、反射或前景遮挡形成柔和过渡",
                "固定机位配合轻微变焦，保留空间呼吸感和氛围层次",
                "镜头贴近环境元素做小幅滑动，形成可剪辑的转场运动",
            ],
            seed,
        )
    if role == "end_copy_space":
        return _pick_variant(
            [
                "宽幅静态微推，主体偏一侧，保留大面积干净留白",
                "远景缓慢横移，维持安静收尾感和可放标题的干净区域",
                "轻微上升或后退，拉开空间关系并形成片尾背景感",
            ],
            seed,
        )
    if motion and motion not in {"轻微横移", "缓慢推近", "轻微推近"}:
        return f"{motion}，主体保持在画面中心，运动幅度克制稳定"
    return _pick_variant(
        [
            "平视中景缓慢推近，主体保持在画面中心并形成稳定商业素材节奏",
            "稳定机位配合轻微横向滑动，保留空间层次和主体动作的清晰度",
            "长焦浅景深轻微拉近，突出主体动作并弱化背景干扰",
        ],
        seed,
    )


def _infer_video_subject_motion(spec: Dict[str, Any], corpus: str) -> str:
    role = _spec_primary_role(spec)
    if _is_new_energy_vehicle_story(spec, corpus):
        return _infer_nev_video_subject_motion(spec, corpus)
    if re.search(r"楼宇|大楼|建筑|玻璃幕墙|天际线|高层|外立面", corpus):
        if "飞机" in corpus:
            return "建筑保持笔直稳定，右上方飞机平稳掠过天空，云层缓慢漂移"
        return "建筑保持笔直稳定，远处云层、窗内微弱人影或玻璃高光轻轻变化"
    if re.search(r"空会议室|空会议桌|空镜|整洁座位|桌面准备", corpus):
        return "长桌、座椅、文件夹和签字笔保持静止，画面只保留窗光和反射的细微变化"
    if re.search(r"鼓掌|祝贺|认可", corpus):
        return "团队成员进行一轮短促克制的鼓掌，手部动作清楚但幅度不大，表情保持自然专业"
    if re.search(r"握手", corpus):
        return "两位商务人士完成一次自然握手或确认动作，手部轻微收紧后停稳，肩部和袖口保持克制"
    if re.search(r"达成|成功|合影|阵列", corpus):
        return "团队站位基本不变，只出现轻微点头、视线交流或姿态收束，保持正式完成感"
    if re.search(r"签字|签署|笔尖|纸面|合同|文件", corpus):
        return "签字笔轻轻下压或短距离滑过纸面，手腕和袖口只做细微真实移动"
    if re.search(r"会议|讨论|团队|方案|平板|资料", corpus):
        return "人物轻微翻页、点头或用手势指向资料，其他人保持专注倾听，动作幅度小"
    if re.search(r"走廊|大厅|前台|入场|进入|门口", corpus):
        return "商务人士以克制步伐进入或穿过空间，手持文件保持稳定，姿态自然专业"
    if role == "transition_mood":
        return "主体密度保持较低，环境光影、反射、前景遮挡或虚化层次缓慢变化"
    if role == "outcome_emotion":
        return "主体呈现完成、满意、品质确认或积极反馈状态，动作轻微收束并稳定停留"
    if role == "end_copy_space":
        return "主体保持安静完整，画面只保留轻微环境动态，留白区域不被新元素占用"
    action = _clean_video_action_focus(str(spec.get("action") or spec.get("subject") or ""))
    return action or "主体只做一个清楚、克制、可识别的动作，动作幅度小而稳定，避免夸张表演"


def _infer_video_scene_motion(spec: Dict[str, Any], corpus: str) -> str:
    role = _spec_primary_role(spec)
    lighting = str(spec.get("lighting") or "")
    if _is_new_energy_vehicle_story(spec, corpus):
        return _infer_nev_video_scene_motion(spec, corpus)
    if re.search(r"楼宇|大楼|建筑|玻璃幕墙|天际线|高层|外立面", corpus):
        return "玻璃幕墙反光轻微流动，天空和建筑边缘保持干净，不改变楼体结构"
    if re.search(r"空会议室|空会议桌|空镜|整洁座位|桌面准备", corpus):
        return "落地窗光线缓慢变化，桌面和玻璃隔断出现轻微反光，空间保持安静无人物进入"
    if re.search(r"达成|成功|合影|阵列", corpus):
        return "团队站位基本不变，只出现轻微点头、视线交流或姿态收束，保持正式完成感"
    if re.search(r"鼓掌|祝贺|认可", corpus):
        return "窗边光线和背景人物只做轻微变化，鼓掌动作保持真实节奏，不新增无关人物"
    if re.search(r"握手", corpus):
        return "背景团队和窗边光线只做轻微变化，握手主体保持清晰不漂移"
    if re.search(r"签字|签署|笔尖|纸面|合同|文件", corpus):
        return "纸张边缘、手部阴影和浅景深背景有细微变化，桌面秩序保持稳定"
    if re.search(r"走廊|大厅|前台|入场|进入|门口", corpus):
        return "空间透视线保持稳定，背景灯带、地面反光和玻璃隔断产生轻微视差"
    if re.search(r"玻璃|窗|幕墙|反射|城市|晨光|自然光", corpus + lighting):
        return "自然光和反射缓慢变化，在主体边缘、桌面、墙面或环境表面形成轻微高光移动"
    return "背景维持轻微环境动态和真实光影变化，不改变原始构图和主体位置"


def _video_stability_rule(role: str, spec: Dict[str, Any]) -> str:
    if _is_new_energy_vehicle_story(spec, _primary_story_text(spec)):
        return _nev_video_stability_rule(role, spec)
    base = "整体保持企业宣传片级真实视频质感，低饱和色调和柔和自然光稳定，镜头运动平滑"
    if role == "detail_closeup":
        return f"{base}，细节纹理、纸张边缘、手部比例和浅景深关系不能跳变"
    if role in {"establishing", "transition_mood", "end_copy_space"}:
        return f"{base}，环境层次、留白区域、建筑线条和光影方向保持稳定"
    if role in {"process_action", "people_usage", "outcome_emotion"}:
        return f"{base}，人物身份、服饰、手部结构、桌面道具和空间位置保持一致"
    return f"{base}，主体外观、材质、空间位置和构图关系保持一致"


def _compose_negative_prompt(frame: Dict[str, Any] | None, fallback: str) -> str:
    sections = frame.get("analysis_sections", {}) if frame else {}
    frame_negative = str(sections.get("【负面提示词】") or sections.get("负面提示词") or "").strip()
    items = _clean_negative_items([
        fallback,
        frame_negative,
        *_as_list(frame.get("negative_prompt_notes") if frame else []),
    ])
    return "不要出现：" + "、".join(items)


def _clean_negative_items(items: Sequence[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for item in items:
        text = _strip_negative_prefix(str(item or ""))
        for part in re.split(r"[、，,。；;\n]+", text):
            cleaned = part.strip(" ：:。；;，,、\t\r\n")
            if not cleaned or cleaned in {"不要出现", "画面不要出现", "参考帧额外避开"}:
                continue
            key = re.sub(r"\s+", "", cleaned).lower()
            if key and key not in seen:
                seen.add(key)
                output.append(cleaned)
    return output


def _reference_usage_label(usage_role: str) -> str:
    return {
        "composition_light": "构图光线参考",
        "light_mood": "光影氛围参考",
        "action_pose": "动作姿态参考",
        "material_detail": "材质细节参考",
        "scene_relation": "人物关系参考",
        "emotion_result": "成果情绪参考",
        "composition_only": "构图参考",
        "style_only": "风格参考",
        "visual_reference": "视觉参考",
        "evidence_only": "证据参考",
        "original_planning": "原创规划",
    }.get(usage_role, "视觉参考")


def _reference_focus_instruction(usage_role: str) -> str:
    return {
        "composition_light": "空间结构、主体位置、透视线条、窗光方向、玻璃反射、景深层次和整体商务质感",
        "light_mood": "光线方向、明暗关系、反射节奏、留白区域、色彩氛围和转场呼吸感",
        "action_pose": "动作姿态、手部关系、人物间距、动作发生位置、镜头裁切和浅景深关系",
        "material_detail": "材质纹理、手部或道具局部、纸张/金属/布料质感、焦点位置和背景虚化",
        "scene_relation": "人物站位或坐席关系、前中后景层次、团队互动距离和场景真实感",
        "emotion_result": "达成后的主体关系、姿态反馈、团队氛围、画面重心和积极但克制的情绪",
        "composition_only": "画面比例、主体位置、空间关系、留白方向和透视结构",
        "style_only": "光线、色彩、质感、清晰度和商业摄影风格",
        "visual_reference": "构图、光线、色彩、主体关系和镜头语言",
    }.get(usage_role, "构图、光线、色彩、主体关系和镜头语言")


def _reference_asset_label(frame: Dict[str, Any], index: int) -> str:
    sheet = str(frame.get("sheet_label") or f"#{index:04d}").strip()
    usage_label = _reference_usage_label(_reference_usage_role(frame))
    brief = str(frame.get("prompt_ready_brief") or frame.get("visual_summary") or "").strip()
    if not brief:
        sections = frame.get("analysis_sections", {})
        brief = _compact_join([sections.get("主体"), sections.get("背景"), sections.get("构图")])
    brief = re.sub(r"\s+", "", brief)
    return f"{sheet} {usage_label} - {brief[:18] or '精选参考帧'}"


def _reference_usage_for_shot(
    frame: Dict[str, Any] | None,
    spec: Dict[str, Any],
    storyboard_lane: str = "main",
    reference_role: str = "standalone",
    anchor_shot_id: str | None = None,
) -> str:
    if reference_role == "derived_view":
        return _anchor_reference_usage_for_shot(spec, anchor_shot_id)
    if not frame:
        return "本镜头不使用具体参考图，按本镜头的主体、空间、构图、光线和商业素材逻辑原创生成。"
    usage_role = _reference_usage_role(frame)
    if usage_role == "evidence_only":
        return "这张图只作为市场证据，不作为当前镜头的 image2 视觉参考。"
    focus = _reference_focus_instruction(usage_role)
    brief = str(frame.get("prompt_ready_brief") or frame.get("visual_summary") or "").strip()
    if not brief:
        sections = frame.get("analysis_sections", {})
        brief = _compact_join([sections.get("主体"), sections.get("背景"), sections.get("构图"), sections.get("光线")])
    brief = _sanitize_reference_brief(brief)
    lane_note = (
        "这张图会先生成锚点主画面；后续延展镜头必须参考锚点图保持同一空间、人物气质、服装和光线，而不是继续直接复刻上传参考图。"
        if storyboard_lane == "extension"
        else ""
    )
    subject = str(spec.get("subject") or "").strip()
    return "；".join(
        part
        for part in [
            f"参考这张图的{focus}",
            f"可借鉴画面：{brief}" if brief else "",
            f"当前镜头仍以“{subject}”为主体，场景和动作必须服从本镜头描述",
            lane_note,
            "不要照搬原图人物身份、可读文字、Logo、水印、真实品牌、真实公司、具体签名或可识别建筑细节",
        ]
        if part
    )


def _anchor_reference_usage_for_shot(spec: Dict[str, Any], anchor_shot_id: str | None) -> str:
    subject = str(spec.get("subject") or "").strip()
    anchor_text = f"分镜 {anchor_shot_id}" if anchor_shot_id else "上一张锚点图"
    return (
        f"本镜头不再直接参考上传原图，而是以上游{anchor_text}生成后的锚点图为 image2 参考；"
        "必须保持锚点图里的同一空间结构、人物气质、服装体系、光线方向、色彩氛围和商业质感；"
        f"当前镜头主体仍以“{subject}”为准，只改变机位、景别、前景遮挡、动作阶段或留白方向，"
        "形成同一场景连续素材；不要重新生成另一套不相干人物、办公室、城市背景或光线。"
    )


def _reference_usage_text(frame: Dict[str, Any] | None) -> str:
    if not frame:
        return "本镜头不绑定具体参考图，由主题、市场需求和素材包情景逻辑原创规划。"
    role_tags = "、".join(_as_list(frame.get("shot_role_tags")))
    composition_tags = "、".join(_as_list(frame.get("composition_tags")))
    brief = str(frame.get("prompt_ready_brief") or frame.get("visual_summary") or "").strip()
    if not brief:
        sections = frame.get("analysis_sections", {})
        brief = _compact_join([sections.get("主体"), sections.get("背景"), sections.get("构图"), sections.get("光线")])
    brief = _sanitize_reference_brief(brief)
    reuse_budget = _reference_reuse_budget(frame)
    usage_role = _reference_usage_role(frame)
    if usage_role == "evidence_only":
        return "这张图只作为市场证据和人工检查材料，不作为 image2 生图参考。"
    usage_label = _reference_usage_label(usage_role)
    focus = _reference_focus_instruction(usage_role)
    parts = [
        f"请参考这张图的{usage_label}，重点借鉴{focus}",
    ]
    if brief:
        parts.append(f"参考图画面说明：{brief}")
    parts.append("在当前镜头中只把它作为视觉依据，主体、场景和动作必须服从本镜头提示词")
    parts.append("不要照搬原图人物身份、可读文字、Logo、水印、真实品牌、真实公司、具体签名或可识别建筑细节")
    if reuse_budget > 1:
        parts.append(f"这张图最多只用于 {reuse_budget} 个同语义镜头的不同机位或不同景别参考，不要生成同构图复制画面")
    if role_tags:
        parts.append(f"适合参考的镜头类型：{role_tags}")
    if composition_tags:
        parts.append(f"可借鉴的构图标签：{composition_tags}")
    if frame.get("risk_flags"):
        parts.append(f"避开风险：{'、'.join(_as_list(frame.get('risk_flags')))}")
    return "；".join(parts) or f"参考帧 {frame.get('frame_id', '')}：用于构图、光线、色彩和镜头语言参考。"


def _anchor_reference_usage_text(anchor_shot_id: str | None, frame: Dict[str, Any] | None = None) -> str:
    source_hint = ""
    if frame:
        brief = _sanitize_reference_brief(str(frame.get("prompt_ready_brief") or frame.get("visual_summary") or ""))
        source_hint = f"；原始参考帧只作为锚点图的来源线索：{brief}" if brief else ""
    anchor_text = f"分镜 {anchor_shot_id}" if anchor_shot_id else "上一张锚点图"
    return (
        f"本镜头为锚点延展镜头，必须以上游{anchor_text}生成图为直接 image2 参考，"
        "保持同一场景、同一人物气质、同一服装体系、同一光线色调和空间连续性；"
        "只允许改变机位、景别、动作阶段、前景遮挡或留白方向，不再直接连接上传原始参考图。"
        f"{source_hint}"
    )


def _sanitize_reference_brief(brief: str) -> str:
    text = str(brief or "").strip()
    text = re.sub(r"高度还原原图的?", "", text)
    text = text.replace("高度还原原图", "")
    text = text.replace("还原原图", "参考")
    text = text.replace("复刻原图", "参考画面")
    return re.sub(r"\s+", " ", text).strip(" ；。")


def _parse_analysis_sections(text: str) -> Dict[str, str]:
    output: Dict[str, str] = {}
    current_label = ""
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        prompt_label = line.strip("：:")
        if prompt_label in {"【中文生图提示词】", "【负面提示词】"}:
            current_label = prompt_label
            output.setdefault(current_label, "")
            continue
        matched_label = ""
        for label in SECTION_LABELS:
            if line.startswith(f"{label}：") or line.startswith(f"{label}:"):
                matched_label = label
                break
        if matched_label:
            current_label = matched_label
            if "：" in line:
                output[current_label] = line.split("：", 1)[1].strip()
            else:
                output[current_label] = line.split(":", 1)[1].strip()
        elif current_label:
            output[current_label] = (output.get(current_label, "") + " " + line).strip()
    return output


def _classify_frame(frame: Dict[str, Any]) -> List[str]:
    text = _search_text(frame)
    categories: List[str] = []
    keyword_map = [
        ("handshake", ["握手", "双手", "合作达成"]),
        ("signing", ["签字", "签署", "落笔", "签约", "签名"]),
        ("document", ["合同", "文件", "纸质", "资料", "签字笔", "笔尖"]),
        ("meeting", ["会议", "会议桌", "讨论", "洽谈", "演示", "围绕"]),
        ("tablet", ["平板", "电子设备", "屏幕", "展示"]),
        ("silhouette", ["剪影", "逆光", "落地窗", "窗前"]),
        ("city", ["城市", "高楼", "楼宇", "玻璃幕墙", "天际线", "建筑"]),
        ("office", ["办公室", "办公", "玻璃隔断", "显示器", "键盘"]),
        ("team", ["团队", "多人", "商务人士", "成员"]),
        ("applause", ["鼓掌", "祝贺", "庆祝"]),
        ("industrial", ["工业", "车间", "设备", "参观", "产业", "产线", "机器人", "制造"]),
        ("product", ["产品", "包装", "礼盒", "静物", "电商", "美妆", "食品", "饮料"]),
        ("festival", ["节日", "中秋", "端午", "春节", "月饼", "粽子", "灯笼", "团圆"]),
        ("lab", ["实验室", "科研", "研发", "检测", "试管", "显微", "仪器"]),
        ("medical", ["医疗", "医院", "医生", "护士", "健康", "康复"]),
        ("education", ["教育", "学校", "课堂", "学生", "老师", "校园", "培训"]),
        ("tourism", ["文旅", "旅游", "景区", "古镇", "酒店", "自然风光", "航拍"]),
        ("closeup", ["特写", "近景", "微距", "浅景深"]),
        ("success", ["成功", "达成", "祝贺", "合影", "成果"]),
    ]
    for category, keywords in keyword_map:
        if any(keyword in text for keyword in keywords):
            categories.append(category)
    categories.extend(_as_list(frame.get("shot_role_tags")))
    categories.extend(_as_list(frame.get("composition_tags")))
    if not categories:
        categories.append("main_subject")
    return _unique_items(categories)


def _resolve_topic(project_path: Path) -> str:
    for path in [project_path / "项目清单.json", project_path / "project_manifest.json"]:
        payload = _read_json_default(path, {})
        if isinstance(payload, dict):
            topic = payload.get("project_title") or payload.get("topic")
            if topic:
                return str(topic)
    return DEFAULT_TOPIC


def _load_market_context(project_path: Path) -> Dict[str, Any]:
    market_dir = project_path / RESEARCH_DIR_NAME / MARKET_MINING_DIR_NAME
    summary = _read_json_default(market_dir / "市场反挖摘要.json", _read_json_default(market_dir / "market_mining_summary.json", {}))
    directions_payload = _read_json_default(market_dir / "商业AI方向.json", {})
    directions = directions_payload.get("directions", directions_payload if isinstance(directions_payload, list) else [])
    if not directions and isinstance(summary, dict):
        directions = summary.get("commercial_ai_directions", [])
    return {
        "seed_keywords": summary.get("seed_keywords", []) if isinstance(summary, dict) else [],
        "buyer_search_prompts": summary.get("buyer_search_prompts", []) if isinstance(summary, dict) else [],
        "top_directions": [
            item.get("direction_name") or item.get("name") or item.get("title")
            for item in directions[:8]
            if isinstance(item, dict)
        ],
    }


def _read_json_default(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return read_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default


def _resolve_path(value: Any, project_path: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    return project_path / path


def _file_url(path: Path) -> str:
    try:
        return path.resolve().as_uri()
    except ValueError:
        return str(path)


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")[:48] or "frame"


def _search_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_search_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_search_text(item) for item in value)
    return str(value or "")


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r"[、,，/|]+", text) if item.strip()]


def _unique_items(items: Sequence[Any]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _strip_negative_prefix(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"^(画面)?不要出现[：:]\s*", "", value)
    value = re.sub(r"^负面提示词[：:]\s*", "", value)
    return value.strip()


def _normalize_frame_analysis(frame: Dict[str, Any]) -> Dict[str, Any]:
    analysis = frame.get("analysis", {}) if isinstance(frame.get("analysis"), dict) else {}
    sections = frame.get("analysis_sections", {}) if isinstance(frame.get("analysis_sections"), dict) else {}
    text = _search_text([analysis, sections, frame])
    risk_text = _search_text([
        analysis.get("risk_flags"),
        analysis.get("visual_summary"),
        analysis.get("prompt_ready_brief"),
        sections.get("主体"),
        sections.get("背景"),
        sections.get("构图"),
        sections.get("视角/镜头"),
        sections.get("光线"),
        sections.get("色彩"),
        sections.get("材质与细节"),
        sections.get("情绪氛围"),
    ])

    risk_flags = _unique_items(_as_list(analysis.get("risk_flags")))
    risk_detection_text = _strip_negative_risk_instructions(risk_text)
    for label, keywords in [
        ("文字风险", ["文字", "字幕", "可读", "乱码"]),
        ("Logo风险", ["Logo", "logo", "标志", "品牌"]),
        ("水印风险", ["水印", "角标"]),
        ("模糊风险", ["模糊", "低清晰", "过暗"]),
        ("多宫格风险", ["多宫格", "拼图"]),
        ("低相关", ["低相关", "不适配"]),
    ]:
        if any(keyword in risk_detection_text for keyword in keywords) and label not in risk_flags:
            risk_flags.append(label)

    shot_role_tags = _unique_items(_as_list(analysis.get("shot_role_tags")) or _infer_frame_role_tags(text))
    composition_tags = _unique_items(_as_list(analysis.get("composition_tags")) or _infer_frame_composition_tags(text))
    policy = str(analysis.get("reference_use_policy") or "").strip()
    if policy not in {"image2_reference", "composition_only", "style_only", "evidence_only", "exclude"}:
        policy = "composition_only" if any("风险" in item for item in risk_flags) else "image2_reference"
    weight = _clamp_float(analysis.get("image2_usage_weight"), 0.0, 1.0, default=0.8)
    if policy in {"evidence_only", "exclude"}:
        weight = 0.0
    elif policy in {"composition_only", "style_only"}:
        weight = min(weight, 0.45)

    prompt_ready_brief = str(
        analysis.get("prompt_ready_brief")
        or sections.get("【中文生图提示词】")
        or _compact_join([sections.get("主体"), sections.get("背景"), sections.get("构图"), sections.get("光线")])
        or analysis.get("visual_summary")
        or frame.get("frame_id")
        or ""
    ).strip()
    negative_notes = _as_list(analysis.get("negative_prompt_notes"))
    if sections.get("【负面提示词】"):
        negative_notes.extend(_as_list(_strip_negative_prefix(str(sections.get("【负面提示词】")))))

    normalized = {
        "visual_summary": str(analysis.get("visual_summary") or prompt_ready_brief).strip(),
        "subject_type": str(analysis.get("subject_type") or _infer_subject_type(text)).strip(),
        "scene_type": str(analysis.get("scene_type") or _infer_scene_type(text)).strip(),
        "shot_role_tags": shot_role_tags,
        "composition_tags": composition_tags,
        "motion_potential": str(analysis.get("motion_potential") or _infer_motion_potential(shot_role_tags)).strip(),
        "commercial_use_cases": _unique_items(_as_list(analysis.get("commercial_use_cases")) or _use_cases_from_roles(shot_role_tags)),
        "topic_fit_score": int(_clamp_float(analysis.get("topic_fit_score"), 0, 100, default=70)),
        "image2_usage_weight": weight,
        "reference_use_policy": policy,
        "risk_flags": risk_flags,
        "prompt_ready_brief": prompt_ready_brief,
        "negative_prompt_notes": _unique_items(negative_notes),
    }
    normalized["reuse_budget"] = _reference_reuse_budget(normalized)
    normalized["reuse_reason"] = _reference_reuse_reason(normalized, int(normalized["reuse_budget"]))
    return normalized


def _compact_join(values: Sequence[Any]) -> str:
    return "，".join(str(value).strip() for value in values if str(value or "").strip())


def _strip_negative_risk_instructions(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"(?:不要|禁止|避免|不保留|无)[^。；;\n]{0,30}(?:文字|字幕|可读|乱码|Logo|logo|标志|品牌|水印|角标)", "", value)
    value = re.sub(r"(?:文字|字幕|可读|乱码|Logo|logo|标志|品牌|水印|角标)[^。；;\n]{0,20}(?:不要|禁止|避免|不保留)", "", value)
    return value


def _clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _infer_frame_role_tags(text: str) -> List[str]:
    tags: List[str] = []
    has_closeup = any(keyword in text for keyword in ["极近", "微距", "特写", "近景局部", "手部局部", "笔尖", "钢笔", "纸面", "袖口"])
    has_wide_space = any(keyword in text for keyword in ["远景", "中远景", "宽幅", "全景", "航拍", "城市", "楼宇", "建筑", "玻璃幕墙", "会议室空间", "办公室空间", "落地窗", "窗景"])
    has_action = any(keyword in text for keyword in ["握手", "签字", "签署", "翻页", "递交", "触摸", "操作", "走入", "鼓掌", "讨论", "交流"])
    has_people = any(keyword in text for keyword in ["人物", "团队", "多人", "商务人士", "成员", "男士", "女士", "人影"])
    has_mood = any(keyword in text for keyword in ["空镜", "倒影", "反射", "剪影", "光影", "氛围", "过渡", "玻璃幕墙"])
    has_outcome = any(keyword in text for keyword in ["成功", "达成", "庆祝", "鼓掌", "见证", "认可", "满意"])
    has_copy_space = any(keyword in text for keyword in ["留白", "片尾", "标题", "收尾", "大面积纸面", "大面积天空"])

    if has_wide_space and not has_closeup:
        tags.append("establishing")
    if has_action:
        tags.append("process_action")
    if has_closeup:
        tags.append("detail_closeup")
    if has_people and not (has_closeup and not has_action):
        tags.append("people_usage")
    if has_mood and not (has_closeup and "反射" not in text and "剪影" not in text):
        tags.append("transition_mood")
    if has_outcome and not has_closeup:
        tags.append("outcome_emotion")
    if has_copy_space and not has_closeup and (has_wide_space or "留白" in text):
        tags.append("end_copy_space")
    if not tags:
        tags.append("main_subject")
    elif "main_subject" not in tags and not has_closeup:
        tags.append("main_subject")
    return _unique_items(tags)


def _infer_frame_composition_tags(text: str) -> List[str]:
    tags: List[str] = []
    keyword_map = [
        ("wide", ["远景", "全景", "宽幅", "航拍"]),
        ("medium", ["中景", "中近景", "中远景"]),
        ("closeup", ["特写", "近景"]),
        ("macro", ["微距", "笔尖", "纹理"]),
        ("top_view", ["俯拍", "顶视"]),
        ("low_angle", ["低机位", "仰拍"]),
        ("silhouette", ["剪影", "逆光"]),
        ("copy_space", ["留白", "空白"]),
        ("symmetry", ["对称", "居中"]),
        ("depth", ["纵深", "前景", "中景", "背景", "景深"]),
        ("reflection", ["反射", "倒影", "玻璃"]),
    ]
    for tag, keywords in keyword_map:
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags or ["medium"]


def _infer_subject_type(text: str) -> str:
    for subject_type, keywords in [
        ("人物", ["人物", "人像", "团队", "商务人士", "医生", "学生", "游客", "工人", "工程师"]),
        ("产品", ["产品", "包装", "礼盒", "静物", "饮料", "食品", "美妆"]),
        ("建筑空间", ["建筑", "楼宇", "城市", "办公室", "会议室", "景区", "室内空间"]),
        ("工业设备", ["设备", "机械", "产线", "车间", "机器人"]),
        ("科研医疗", ["实验", "科研", "医疗", "医院", "检测", "仪器"]),
        ("自然景观", ["山", "海", "森林", "天空", "自然风光"]),
        ("节日道具", ["节日", "粽子", "月饼", "灯笼", "礼盒"]),
    ]:
        if any(keyword in text for keyword in keywords):
            return subject_type
    return "核心主体"


def _infer_scene_type(text: str) -> str:
    for scene_type, keywords in [
        ("商业办公空间", ["办公室", "会议室", "商务", "会议桌", "玻璃隔断"]),
        ("城市建筑空间", ["城市", "楼宇", "建筑", "天际线", "幕墙"]),
        ("工业生产空间", ["工厂", "车间", "产线", "制造"]),
        ("科研实验空间", ["实验室", "研发", "检测", "仪器"]),
        ("医疗健康空间", ["医院", "诊室", "医疗", "康复"]),
        ("教育学习空间", ["学校", "课堂", "校园", "培训"]),
        ("文旅户外空间", ["景区", "旅游", "古镇", "自然风光", "酒店"]),
        ("产品静物空间", ["静物", "电商", "产品展示", "包装"]),
        ("节日生活空间", ["节日", "团圆", "礼赠", "餐桌"]),
    ]:
        if any(keyword in text for keyword in keywords):
            return scene_type
    return "真实商业素材场景"


def _infer_motion_potential(role_tags: Sequence[str]) -> str:
    if "process_action" in role_tags:
        return "适合做小幅跟随、侧移或推近，突出一个明确动作瞬间。"
    if "detail_closeup" in role_tags:
        return "适合微距推近或轻微焦点转移，突出材质和局部细节。"
    if "establishing" in role_tags or "end_copy_space" in role_tags:
        return "适合稳定推近、横移或轻微上升，保留空间层次和留白。"
    if "transition_mood" in role_tags:
        return "适合缓慢横移、变焦或光影流动，作为段落转场。"
    return "适合稳定微推，让主体保持清晰并产生轻微真实动态。"


def _use_cases_from_roles(role_tags: Sequence[str]) -> List[str]:
    mapping = {
        "establishing": "片头建立",
        "main_subject": "主体展示",
        "process_action": "过程动作",
        "detail_closeup": "细节特写",
        "people_usage": "人物/使用场景",
        "transition_mood": "转场氛围",
        "outcome_emotion": "成果情绪",
        "end_copy_space": "结尾留白",
    }
    return [mapping[tag] for tag in role_tags if tag in mapping] or ["商业素材参考"]


def _build_diversity_report(
    storyboard_master: Sequence[Dict[str, Any]],
    reference_plan_items: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    group_counts: Dict[str, int] = {}
    subject_counts: Dict[str, int] = {}
    composition_counts: Dict[str, int] = {}
    reference_counts: Dict[str, int] = {}
    for shot in storyboard_master:
        group = str(shot.get("scene_group") or "")
        subject = str(shot.get("subject_main") or "")
        composition = str(shot.get("composition_notes") or "")
        group_counts[group] = group_counts.get(group, 0) + 1
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
        composition_key = composition[:24]
        composition_counts[composition_key] = composition_counts.get(composition_key, 0) + 1
    for item in reference_plan_items:
        for frame_id in item.get("reference_frame_ids") or []:
            frame_key = str(frame_id)
            reference_counts[frame_key] = reference_counts.get(frame_key, 0) + 1
    return {
        "scene_group_counts": group_counts,
        "unique_subject_count": len([key for key in subject_counts if key]),
        "repeated_subjects": {key: value for key, value in subject_counts.items() if value > 3},
        "repeated_compositions": {key: value for key, value in composition_counts.items() if value > 4},
        "reference_reuse_counts": reference_counts,
        "high_reuse_reference_frame_ids": [key for key, value in reference_counts.items() if value > 3],
    }


def _secondary_for(subject: str, action: str) -> List[str]:
    text = f"{subject} {action}"
    items = []
    for keyword in ["合同文件", "签字笔", "会议桌", "平板设备", "玻璃窗", "团队成员", "城市背景", "深色西装"]:
        if keyword[:2] in text or len(items) < 4:
            items.append(keyword)
    return items[:4]


def _scene_for_group(group: str) -> str:
    if "城市" in group or "结尾" in group:
        return "现代城市高层办公楼、玻璃幕墙、明亮会议室和窗边商务空间"
    if "准备" in group or "条款" in group or "签约" in group:
        return "现代明亮会议室，白色会议桌、纸质合同、签字笔、平板设备和柔和窗光"
    if "洽谈" in group:
        return "玻璃隔断会议室，双方团队围绕会议桌进行正式商务沟通"
    if "握手" in group:
        return "签约完成后的现代会议室或落地窗前商务空间"
    return "现代企业办公区、会议室、走廊和合作执行空间"


def _shot_type_from_composition(composition: str) -> str:
    if "特写" in composition or "微距" in composition:
        return "特写，浅景深"
    if "俯拍" in composition:
        return "俯拍中近景"
    if "远景" in composition:
        return "宽幅远景"
    if "中远景" in composition:
        return "中远景"
    if "中近景" in composition:
        return "中近景"
    return "中景"


def _camera_angle_from_composition(composition: str) -> str:
    if "低机位" in composition:
        return "低机位平视略仰角"
    if "俯拍" in composition:
        return "俯拍视角"
    if "微距" in composition or "特写" in composition:
        return "近距离浅景深镜头"
    return "平视真实摄影镜头"


def _lighting_for_group(group: str, beat_index: int) -> str:
    if "城市" in group or "结尾" in group:
        return "窗边自然光与玻璃反射形成柔和逆光，明暗对比克制"
    if "签约" in group or "条款" in group:
        return "明亮柔和的会议室窗光，白色桌面反光，手部和文件清晰"
    if "握手" in group:
        return "柔和侧逆光突出握手轮廓，背景轻微虚化"
    if beat_index % 3 == 0:
        return "明亮冷白办公光与自然窗光混合，人物面部和桌面细节清楚"
    return "大面积自然窗光，低对比阴影，干净专业的商务氛围"
