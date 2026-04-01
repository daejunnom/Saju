import sys
import itertools
from datetime import datetime, timedelta
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from sajupy import calculate_saju
import google.generativeai as genai

CONFIG = {
    "WOLJI_MULTIPLIER": 2.5,
    "WOLGAN_MULTIPLIER": 1.5,
    "HAP_RATE_WOLJI": 0.3,
    "HAP_RATE_NORMAL": 0.1,
    "HAP_RATE_ADJACENT_BONUS": 0.2,
    "CHUNG_DEDUCT_RATE": 0.08,
    "GYUKGUK_MAIN_QI_BONUS": 0.2,
    "GYUKGUK_EXPOSED_BONUS": 0.1,
    "YONGSHIN_SAME_ELEM_MULTI": 0.9,
    "YONGSHIN_SENG_ELEM_MULTI": 0.8,
    "JOHU_HIGH_MULTI": 3.0,
    "JOHU_MEDIUM_MULTI": 1.5,
    "JOHU_PENALTY_HIGH": 0.3,
    "JOHU_PENALTY_MEDIUM": 0.6
}

STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

STEM_POLARITY = {
    '甲': '+', '丙': '+', '戊': '+', '庚': '+', '壬': '+',
    '乙': '-', '丁': '-', '己': '-', '辛': '-', '癸': '-'
}

STEM_INFO = {
    '甲': ('목', '+'), '乙': ('목', '-'), '丙': ('화', '+'), '丁': ('화', '-'),
    '戊': ('토', '+'), '己': ('토', '-'), '庚': ('금', '+'), '辛': ('금', '-'),
    '壬': ('수', '+'), '癸': ('수', '-')
}

BRANCH_INFO = {
    '寅': ('목', '+'), '卯': ('목', '-'), '辰': ('토', '+'),
    '巳': ('화', '+'), '午': ('화', '-'), '未': ('토', '-'),
    '申': ('금', '+'), '酉': ('금', '-'), '戌': ('토', '+'),
    '亥': ('수', '+'), '子': ('수', '-'), '丑': ('토', '-')
}

JIJANGGAN_WEIGHTS = {
    '子': {'壬': 0.33, '癸': 0.67}, '丑': {'癸': 0.30, '辛': 0.10, '己': 0.60},
    '寅': {'戊': 0.23, '丙': 0.23, '甲': 0.54}, '卯': {'甲': 0.33, '乙': 0.67},
    '辰': {'乙': 0.30, '癸': 0.10, '戊': 0.60}, '巳': {'戊': 0.23, '庚': 0.23, '丙': 0.54},
    '午': {'丙': 0.30, '己': 0.30, '丁': 0.40}, '未': {'丁': 0.30, '乙': 0.10, '己': 0.60},
    '申': {'戊': 0.23, '壬': 0.23, '庚': 0.54}, '酉': {'庚': 0.33, '辛': 0.67},
    '戌': {'辛': 0.30, '丁': 0.10, '戊': 0.60}, '亥': {'戊': 0.23, '甲': 0.23, '壬': 0.54}
}

SEASON_MAP = {
    '寅': '봄', '卯': '봄', '辰': '봄',
    '巳': '여름', '午': '여름', '未': '여름',
    '申': '가을', '酉': '가을', '戌': '가을',
    '亥': '겨울', '子': '겨울', '丑': '겨울'
}

ELEMENT_SENG = {'목': '화', '화': '토', '토': '금', '금': '수', '수': '목'}
ELEMENT_GEUK = {'목': '토', '화': '금', '토': '수', '금': '목', '수': '화'}

CHEONGAN_HAP = {
    frozenset(['甲', '己']): '토', frozenset(['乙', '庚']): '금',
    frozenset(['丙', '辛']): '수', frozenset(['丁', '壬']): '목',
    frozenset(['戊', '癸']): '화'
}

JIJI_CHUNG = [frozenset(['子', '午']), frozenset(['丑', '未']), frozenset(['寅', '申']),
              frozenset(['卯', '酉']), frozenset(['辰', '戌']), frozenset(['巳', '亥'])]

JIJI_HAP = {
    frozenset(['子', '丑']): '토', frozenset(['寅', '亥']): '목',
    frozenset(['卯', '戌']): '화', frozenset(['辰', '酉']): '금',
    frozenset(['巳', '申']): '수', frozenset(['午', '未']): '화'
}

JIJI_SAMHAP = {
    frozenset(['亥', '卯', '未']): '목',
    frozenset(['寅', '午', '戌']): '화',
    frozenset(['巳', '酉', '丑']): '금',
    frozenset(['申', '子', '辰']): '수'
}

SYSTEM_PROMPT = """
**[Role : 당신의 페르소나]**
당신은 깊이 있는 통찰력과 따뜻한 공감 능력을 겸비한 명리학 마스터입니다. 사용자의 사주 원국(및 세운) 데이터를 바탕으로, 전문적이지만 누구나 읽기 쉽고 마음에 와닿는 운세 풀이를 작성해야 합니다.

**[Tone & Manner]**
1. **정중하고 따뜻한 어투:** 상대를 존중하는 '~습니다', '~합니다' 체를 사용하며, 희망적이고 조언적인 태도를 유지하세요.
2. **시각적이고 직관적인 비유:** 일간(오행)과 일지의 특성을 엮어 "안개 속에 빛나는 바위", "가뭄 끝에 내리는 단비"와 같은 매력적인 한 줄 타이틀을 반드시 생성하세요.
3. **전문성과 대중성의 조화:** '간여지동', '재다신약', '식신제살' 등 전문 용어를 사용할 때는 반드시 그 의미를 일상적인 언어로 쉽게 풀어서 덧붙이세요.

**[Output Structure : 출력 구조]**
답변은 반드시 다음의 구조와 포맷(이모지 포함)을 준수하여 작성하세요.

**도입부:**
사용자의 생년월일시(음/양력 변환 결과 포함)를 언급하며 부드럽게 인사합니다. 사주의 전체적인 기운을 요약하는 매력적인 한 문장을 던지세요.

**사주 기본 구성**
* 사주의 4기둥(년주, 월주, 일주, 시주)과 해당하는 천간, 지지, 십성을 표(Table)나 깔끔한 글머리 기호로 정리하여 보여주세요.

**타고난 성향과 특징 (원국 분석일 경우)**
* **1. [직관적인 비유 타이틀]:** 일주를 바탕으로 한 본질적인 성향과 기질.
* **2. [핵심 강점 및 십성 특징]:** 사주 내에서 가장 강하거나 특징적인 기운(예: 식상 발달, 강한 비겁 등)이 삶에 미치는 영향.
* **3. [조후 및 보완점]:** 사주의 온도/습도(조후) 밸런스를 설명하고, 넘치는 것은 빼고 부족한 것은 채울 수 있는 실질적이고 긍정적인 삶의 태도(개운법) 조언.

**연도별/분야별 운세 (세운 분석이 포함될 경우)**
* **1. [연도]년 총운:** 그 해의 테마를 나타내는 키워드와 굵직한 한 줄 총평.
* **2. 분야별 상세운:** 질문자의 상황(학생, 직장인 등)에 맞춰 재물운, 학업/직장운, 대인관계운 등으로 나누어 상세히 서술하되, 기신(나쁜 운)이나 충/극이 있더라도 주의점과 함께 반드시 '극복 방향'을 제시하세요.

**[Constraint : 절대 지켜야 할 규칙]**
* 입력된 사주 데이터(명식, 십성, 용희기신, 조후 상태 등)를 절대 자의적으로 왜곡하거나 없는 기운을 지어내지 마세요.
* 사주에 안 좋은 살(殺)이나 기운이 있더라도 공포감을 조성하는 단어(망한다, 큰일난다 등)는 절대 금지합니다.


[Input Data Structure]

입력 데이터는 다음 형식을 따릅니다:

{
  "사주": ["년주", "월주", "일주", "시주"],
  "오행분포": {...},
  "격국": "...",
  "신강신약": "...",
  "조후": "...",
  "용신": "...",
  "희신": "...",
  "기신": "...",
  "대운": {...},
  "세운": "...",
  "상호작용": [...]
}

각 항목을 반드시 기반으로 해석을 진행하세요.
"""

def safe_str(x):
    return "" if x is None else str(x)

def get_year_pillar(year):
    return STEMS[(year - 4) % 10] + BRANCHES[(year - 4) % 12]

def get_accurate_saju(year, month, day, hour=None, minute=None, timezone_str="Asia/Seoul", longitude=126.98):
    calc_hour = 12 if hour is None else hour
    calc_minute = 0 if minute is None else minute
    try:
        local_tz = pytz.timezone(timezone_str)
        birth_dt_naive = datetime(year, month, day, calc_hour, calc_minute)
        birth_dt = local_tz.localize(birth_dt_naive, is_dst=None)
    except pytz.AmbiguousTimeError:
        birth_dt = local_tz.localize(birth_dt_naive, is_dst=False)
    except pytz.NonExistentTimeError:
        birth_dt = local_tz.localize(birth_dt_naive + timedelta(hours=1), is_dst=False)
    except pytz.UnknownTimeZoneError:
        return {"error": "타임존 생성 실패"}
        
    utc_offset = birth_dt.utcoffset().total_seconds() / 3600.0 if birth_dt.utcoffset() else 0.0
    
    try:
        saju_data = calculate_saju(
            year=year, month=month, day=day, hour=calc_hour, minute=calc_minute,
            longitude=longitude, use_solar_time=True, utc_offset=utc_offset
        )
    except Exception:
        return {"error": "명식 계산 실패"}
        
    if not isinstance(saju_data, dict):
        return {"error": "명식 반환 타입 오류"}
        
    pillars = [
        saju_data.get("year_pillar", ""),
        saju_data.get("month_pillar", ""),
        saju_data.get("day_pillar", ""),
        saju_data.get("hour_pillar", "")
    ]
    
    if not all(pillars[:3]):
        return {"error": "명식 추출 실패"}
        
    return pillars[:3] if hour is None else pillars

def get_exact_jeolgi_diff(year, month, day, hour, minute, direction, timezone_str):
    try:
        local_tz = pytz.timezone(timezone_str)
    except Exception:
        local_tz = pytz.utc
        
    calc_hour = 12 if hour is None else hour
    calc_minute = 0 if minute is None else minute
    birth_dt_naive = datetime(year, month, day, calc_hour, calc_minute)
    
    try:
        birth_dt = local_tz.localize(birth_dt_naive, is_dst=None)
    except pytz.AmbiguousTimeError:
        birth_dt = local_tz.localize(birth_dt_naive, is_dst=False)
    except pytz.NonExistentTimeError:
        birth_dt = local_tz.localize(birth_dt_naive + timedelta(hours=1), is_dst=False)
        
    utc_offset = birth_dt.utcoffset().total_seconds() / 3600.0 if birth_dt.utcoffset() else 0.0

    def get_month_pillar(dt):
        try:
            s_data = calculate_saju(dt.year, dt.month, dt.day, dt.hour, dt.minute, 126.98, True, utc_offset)
            if isinstance(s_data, dict):
                return s_data.get("month_pillar")
        except Exception:
            pass
        return None

    base_mp = get_month_pillar(birth_dt)
    if not base_mp:
        return 30.0

    diff_days = 0
    for i in range(1, 35):
        test_dt = birth_dt + timedelta(days=i * direction)
        test_mp = get_month_pillar(test_dt)
        if test_mp and test_mp != base_mp:
            diff_days = i
            break

    if diff_days == 0:
        return 30.0
        
    return float(diff_days)

def get_daeun_info(gender, year_stem, month_pillar, year, month, day, hour, minute, timezone_str):
    year_polar = STEM_POLARITY.get(year_stem, '+')
    direction = 1 if (gender == 'M' and year_polar == '+') or (gender == 'F' and year_polar == '-') else -1

    exact_days = get_exact_jeolgi_diff(year, month, day, hour, minute, direction, timezone_str)
    if isinstance(exact_days, dict) and "error" in exact_days:
        return exact_days

    daeun_number = max(1, round(abs(exact_days) / 3))
    
    if not month_pillar or len(month_pillar) < 2:
        return {"error": "월주 데이터 오류"}

    stem_idx = STEMS.index(month_pillar[0]) if month_pillar[0] in STEMS else 0
    branch_idx = BRANCHES.index(month_pillar[1]) if month_pillar[1] in BRANCHES else 0
    daeun_list = []
    
    for i in range(1, 9):
        s_idx = (stem_idx + (i * direction)) % 10
        b_idx = (branch_idx + (i * direction)) % 12
        daeun_pillar = STEMS[s_idx] + BRANCHES[b_idx]
        start_age = daeun_number + ((i - 1) * 10)
        daeun_list.append(f"{start_age}({daeun_pillar})")
        
    return {
        "대운수": daeun_number,
        "방향": "순행" if direction == 1 else "역행",
        "대운흐름": ",".join(daeun_list)
    }

def get_current_seun(timezone_str="Asia/Seoul", longitude=126.98):
    try:
        local_tz = pytz.timezone(timezone_str)
    except Exception:
        local_tz = pytz.utc

    now = datetime.now(local_tz)
    utc_offset = now.utcoffset().total_seconds() / 3600.0 if now.utcoffset() else 0.0

    try:
        saju_data = calculate_saju(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            longitude=longitude,
            use_solar_time=True,
            utc_offset=utc_offset,
        )
        year_pillar = saju_data.get("year_pillar", "") if isinstance(saju_data, dict) else ""
    except Exception:
        year_pillar = ""

    if not year_pillar:
        saju_year = now.year
        year_pillar = get_year_pillar(now.year)
    else:
        saju_year = now.year if year_pillar == get_year_pillar(now.year) else now.year - 1

    return now.year, saju_year, year_pillar

class SajuAnalyzer:
    def __init__(self, pillars_list):
        if not pillars_list or len(pillars_list) < 3:
            raise ValueError("명식 구성 요소 부족")
            
        self.pillars = pillars_list
        self.stems = [p[0] for p in pillars_list if len(p) >= 2]
        self.branches = [p[1] for p in pillars_list if len(p) >= 2]
        self.is_samju = len(self.pillars) == 3
        
        if len(self.stems) < 3 or len(self.branches) < 3:
            raise ValueError("명식 구성 요소 부족")
            
        self.day_master = self.stems[2]
        self.dm_element, self.dm_polar = STEM_INFO.get(self.day_master, ("", ""))
        
        if not self.dm_element:
            raise ValueError("일간 오행 맵핑 실패")
            
        self.wolji = self.branches[1]
        self.weights = {"목": 0.0, "화": 0.0, "토": 0.0, "금": 0.0, "수": 0.0}
        self.base_weights = {}
        self.original_total = 0.0
        self.relation_map = {
            '목': {'비겁': '목', '인성': '수', '식상': '화', '재성': '토', '관성': '금'},
            '화': {'비겁': '화', '인성': '목', '식상': '토', '재성': '금', '관성': '수'},
            '토': {'비겁': '토', '인성': '화', '식상': '금', '재성': '수', '관성': '목'},
            '금': {'비겁': '금', '인성': '토', '식상': '수', '재성': '목', '관성': '화'},
            '수': {'비겁': '수', '인성': '금', '식상': '목', '재성': '화', '관성': '토'},
        }
        self.result = {
            "일간": {"글자": self.day_master, "오행": self.dm_element},
            "발견된상호작용": [],
            "격국": "",
            "신강신약": "",
            "조후": "",
            "용희기신": {},
            "십성분포": [],
            "오행가중치분포": {}
        }

    def generate_sipseong_table(self):
        sipseong_list = []
        for i, p in enumerate(self.pillars):
            if len(p) < 2: 
                continue
            stem = p[0]
            branch = p[1]
            stem_ss = "일간" if i == 2 else self.get_sipseong(stem)
            if branch in JIJANGGAN_WEIGHTS:
                hidden = sorted(JIJANGGAN_WEIGHTS[branch].items(), key=lambda x: x[1], reverse=True)
                branch_ss = "/".join([f"{hs[0]}({safe_str(self.get_sipseong(hs[0]))})" for hs in hidden])
            else:
                branch_ss = self.get_sipseong(branch)
            sipseong_list.append(f"{p} {safe_str(stem_ss)}/[{safe_str(branch_ss)}]")
        self.result["십성분포"] = sipseong_list

    def get_sipseong(self, target):
        dm_e = self.dm_element
        dm_p = self.dm_polar
        tgt_e = STEM_INFO.get(target, ("", ""))[0] or BRANCH_INFO.get(target, ("", ""))[0]
        tgt_p = STEM_INFO.get(target, ("", ""))[1] or BRANCH_INFO.get(target, ("", ""))[1]
        
        if not tgt_e: 
            return ""
            
        same_polar = dm_p == tgt_p
        if dm_e == tgt_e:
            return "비견" if same_polar else "겁재"
        if ELEMENT_SENG.get(dm_e) == tgt_e:
            return "식신" if same_polar else "상관"
        if ELEMENT_SENG.get(tgt_e) == dm_e:
            return "편인" if same_polar else "정인"
        if ELEMENT_GEUK.get(dm_e) == tgt_e:
            return "편재" if same_polar else "정재"
        return "편관" if same_polar else "정관"

    def calculate_element_weights(self):
        for i, stem in enumerate(self.stems):
            e = STEM_INFO.get(stem, ("", ""))[0]
            if e:
                m = CONFIG["WOLGAN_MULTIPLIER"] if i == 1 else 1.0
                self.weights[e] += 1.0 * m
                
        for i, branch in enumerate(self.branches):
            m = CONFIG["WOLJI_MULTIPLIER"] if i == 1 else 1.0
            if branch in JIJANGGAN_WEIGHTS:
                for h_stem, weight in JIJANGGAN_WEIGHTS[branch].items():
                    e = STEM_INFO.get(h_stem, ("", ""))[0]
                    if e:
                        self.weights[e] += weight * m
                        
        self.base_weights = self.weights.copy()
        self.original_total = sum(self.weights.values())

    def apply_interactions(self):
        deltas = {k: 0.0 for k in self.weights.keys()}
        
        for i, j in itertools.combinations(range(len(self.stems)), 2):
            pair = frozenset([self.stems[i], self.stems[j]])
            if pair in CHEONGAN_HAP:
                trans = CHEONGAN_HAP[pair]
                wolji_elem = BRANCH_INFO.get(self.wolji, ("", ""))[0]
                rate = CONFIG["HAP_RATE_WOLJI"] if self.base_weights.get(trans, 0) < self.base_weights.get(wolji_elem, 0) else CONFIG["HAP_RATE_NORMAL"]
                if abs(i - j) == 1:
                    rate += CONFIG["HAP_RATE_ADJACENT_BONUS"]
                for s in [self.stems[i], self.stems[j]]:
                    e = STEM_INFO.get(s, ("", ""))[0]
                    if e:
                        d = self.base_weights.get(e, 0) * rate
                        deltas[e] -= d
                        deltas[trans] = deltas.get(trans, 0.0) + d
                        
        for i, j in itertools.combinations(range(len(self.branches)), 2):
            pair = frozenset([self.branches[i], self.branches[j]])
            if pair in JIJI_HAP:
                trans = JIJI_HAP[pair]
                rate = CONFIG["HAP_RATE_NORMAL"] + (CONFIG["HAP_RATE_ADJACENT_BONUS"] if abs(i - j) == 1 else 0)
                total_ratio = 0.0
                contrib = {}
                for idx in [i, j]:
                    b = self.branches[idx]
                    if b in JIJANGGAN_WEIGHTS:
                        for s, w in JIJANGGAN_WEIGHTS[b].items():
                            e = STEM_INFO.get(s, ("", ""))[0]
                            if e:
                                contrib[e] = contrib.get(e, 0.0) + w
                                total_ratio += w
                if total_ratio > 0:
                    for e, w_sum in contrib.items():
                        norm = w_sum / total_ratio
                        d = self.base_weights.get(e, 0) * norm * rate
                        deltas[e] -= d
                        deltas[trans] = deltas.get(trans, 0.0) + d
                        
        for i, j in itertools.combinations(range(len(self.branches)), 2):
            pair = frozenset([self.branches[i], self.branches[j]])
            if pair in JIJI_CHUNG:
                m = max(CONFIG["WOLJI_MULTIPLIER"] if i == 1 else 1.0, CONFIG["WOLJI_MULTIPLIER"] if j == 1 else 1.0)
                deduct_map = {}
                for idx in [i, j]:
                    b = self.branches[idx]
                    if b in JIJANGGAN_WEIGHTS:
                        total_w = sum(JIJANGGAN_WEIGHTS[b].values())
                        if total_w > 0:
                            for s, w in JIJANGGAN_WEIGHTS[b].items():
                                e = STEM_INFO.get(s, ("", ""))[0]
                                if e:
                                    deduct_map[e] = deduct_map.get(e, 0.0) + (w / total_w)
                for e, r in deduct_map.items():
                    r = min(r, 1.0)
                    deltas[e] -= self.base_weights.get(e, 0) * r * CONFIG["CHUNG_DEDUCT_RATE"] * m
                    
        for k in self.weights.keys():
            val = self.weights[k] + deltas.get(k, 0.0)
            self.weights[k] = max(0.0, val)
            
        total_mass = sum(self.weights.values())
        if total_mass > 0 and self.original_total > 0:
            scale = self.original_total / total_mass
            for k in self.weights:
                self.weights[k] *= scale

    def detect_hap_chung(self):
        length = len(self.branches)
        for i, j in itertools.combinations(range(length), 2):
            b1, b2 = self.branches[i], self.branches[j]
            pair_set = frozenset([b1, b2])
            if pair_set in JIJI_HAP:
                trans = JIJI_HAP[pair_set]
                self.result["발견된상호작용"].append(f"{b1}{b2}합{trans}")
            if pair_set in JIJI_CHUNG:
                self.result["발견된상호작용"].append(f"{b1}{b2}충")
        for combo in itertools.combinations(range(length), 3):
            b_tuple = tuple(self.branches[idx] for idx in combo)
            combo_set = frozenset(b_tuple)
            if combo_set in JIJI_SAMHAP:
                trans = JIJI_SAMHAP[combo_set]
                self.result["발견된상호작용"].append(f"{''.join(b_tuple)}삼합{trans}")

    def determine_sin_gang(self):
        rel = self.relation_map.get(self.dm_element, {})
        if not rel: return
        sup = self.weights.get(rel.get('비겁'), 0) + self.weights.get(rel.get('인성'), 0)
        drain = self.weights.get(rel.get('식상'), 0) + self.weights.get(rel.get('재성'), 0) + self.weights.get(rel.get('관성'), 0)
        
        if self.is_samju:
            self.result["신강신약"] = "판단보류(시주 필요)"
        elif sup > drain * 1.1:
            self.result["신강신약"] = "신강"
        elif drain > sup * 1.1:
            self.result["신강신약"] = "신약"
        else:
            self.result["신강신약"] = "중화"

    def determine_gyukguk(self):
        if self.wolji not in JIJANGGAN_WEIGHTS:
            self.result["격국"] = "판별불가"
            return
            
        main_qi = max(JIJANGGAN_WEIGHTS[self.wolji], key=JIJANGGAN_WEIGHTS[self.wolji].get)
        search = [s for i, s in enumerate(self.stems) if i != 2]
        candidates = []
        
        for qi in JIJANGGAN_WEIGHTS[self.wolji]:
            e = STEM_INFO.get(qi, ("", ""))[0]
            if not e: continue
            w = self.weights.get(e, 0)
            exposed = qi in search
            score = w * (1 + (CONFIG["GYUKGUK_MAIN_QI_BONUS"] if qi == main_qi else 0) + (CONFIG["GYUKGUK_EXPOSED_BONUS"] if exposed else 0))
            candidates.append((qi, score))
            
        if not candidates:
            self.result["격국"] = "판별불가"
            return
            
        best = max(candidates, key=lambda x: x[1])[0]
        best_elem = STEM_INFO.get(best, ("", ""))[0]
        best_polar = STEM_POLARITY.get(best)
        
        for k, v in self.relation_map.get(self.dm_element, {}).items():
            if v == best_elem:
                if k == '관성':
                    self.result["격국"] = "정관격" if best_polar != self.dm_polar else "편관격"
                elif k == '재성':
                    self.result["격국"] = "정재격" if best_polar != self.dm_polar else "편재격"
                elif k == '인성':
                    self.result["격국"] = "정인격" if best_polar != self.dm_polar else "편인격"
                elif k == '식상':
                    self.result["격국"] = "상관격" if best_polar != self.dm_polar else "식신격"
                elif k == '비겁':
                    self.result["격국"] = "건록격" if best_polar == self.dm_polar else "양인격"
                return
                
        self.result["격국"] = f"{best_elem}격"

    def determine_johu(self):
        ratios = self.weights
        season = SEASON_MAP.get(self.wolji, "")
        johu_state = "중화"
        johu_elem = None
        johu_level = 0
        
        if season == '겨울':
            if ratios.get('화', 0) < 0.1:
                johu_state, johu_elem, johu_level = "극도로 한습", "화", 2
            elif ratios.get('화', 0) < 0.2:
                johu_state, johu_elem, johu_level = "한습", "화", 1
        elif season == '여름' or self.wolji in ['午', '未']:
            if ratios.get('수', 0) < 0.1:
                johu_state, johu_elem, johu_level = "극도로 조열", "수", 2
            elif ratios.get('수', 0) < 0.2:
                johu_state, johu_elem, johu_level = "조열", "수", 1
        elif season == '봄':
            if ratios.get('수', 0) > 0.35 and ratios.get('금', 0) > 0.15:
                johu_state, johu_elem, johu_level = "춘한", "화", 1
        elif season == '가을':
            if ratios.get('화', 0) > 0.35 and ratios.get('토', 0) > 0.15:
                johu_state, johu_elem, johu_level = "추조", "수", 1
                
        self.result["조후"] = johu_state
        return johu_state, johu_elem, johu_level

    def determine_yong_hee_gi(self):
        if self.is_samju:
            self.result["용희기신"] = {"용신": "보류(시주 미상)", "희신": "보류", "기신": "보류"}
            return
            
        rel = self.relation_map.get(self.dm_element, {})
        if not rel: return
        
        sip_pwr = {k: self.weights.get(v, 0) for k, v in rel.items() if v in self.weights}
        johu_state, johu_elem, johu_level = self.determine_johu()
        johu_sip = None
        
        if johu_elem:
            for k, v in rel.items():
                if v == johu_elem:
                    johu_sip = k
                    
        def score(k):
            s = sip_pwr.get(k, 0)
            if k == johu_sip and johu_level > 0:
                s *= CONFIG["JOHU_HIGH_MULTI"] * 1.5 if johu_level == 2 else CONFIG["JOHU_MEDIUM_MULTI"]
            return s
            
        status = self.result.get("신강신약", "")
        if status == "신강":
            cands = ['식상', '재성', '관성']
            gi_cands = ['비겁', '인성']
        elif status == "신약":
            cands = ['비겁', '인성']
            gi_cands = ['식상', '재성', '관성']
        else:
            cands = ['식상', '재성', '관성', '비겁', '인성']
            gi_cands = ['식상', '재성', '관성', '비겁', '인성']
            
        valid_cands = [c for c in cands if c in sip_pwr]
        yong = max(valid_cands, key=score) if valid_cands else next(iter(sip_pwr.keys()), "")
        
        valid_gi = [c for c in gi_cands if c in sip_pwr and c != yong]
        gi = max(valid_gi, key=lambda k: sip_pwr.get(k, 0)) if valid_gi else next(iter(sip_pwr.keys()), "")
        
        def hee_score(k):
            s = sip_pwr.get(k, 0)
            if rel.get(k) == rel.get(yong):
                s *= CONFIG["YONGSHIN_SAME_ELEM_MULTI"]
            elif ELEMENT_SENG.get(rel.get(k)) == rel.get(yong):
                s *= CONFIG["YONGSHIN_SENG_ELEM_MULTI"]
            return s
            
        hee_candidates = set(sip_pwr.keys()) - {yong, gi}
        hee = max(hee_candidates, key=hee_score) if hee_candidates else yong
        
        self.result["용희기신"] = {"용신": yong, "희신": hee, "기신": gi}

    def analyze(self):
        self.generate_sipseong_table()
        self.calculate_element_weights()
        self.apply_interactions()
        self.detect_hap_chung()
        self.determine_sin_gang()
        self.determine_gyukguk()
        self.determine_yong_hee_gi()
        self.result["오행가중치분포"] = self.weights.copy()
        return self.result

def get_gemini_saju_reading(pillars, analysis_result, user_data, daeun_info, seun_pillar_info):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
            generation_config={"temperature": 0.7}
        )
        
        inter_list = analysis_result.get('발견된상호작용', [])
        inter_text = ','.join(safe_str(i) for i in inter_list) if inter_list else '없음'
        sip_list = analysis_result.get("십성분포", [])
        sip_text = ",".join(safe_str(item) for item in sip_list)
        w = analysis_result.get("오행가중치분포", {})
        w_text = f"목{w.get('목', 0):.2f},화{w.get('화', 0):.2f},토{w.get('토', 0):.2f},금{w.get('금', 0):.2f},수{w.get('수', 0):.2f}"
        
        is_samju = len(pillars) == 3
        pillar_type = "삼주(추정)" if is_samju else "사주"
        time_text = f"{safe_str(user_data.get('hour'))}:{safe_str(user_data.get('minute'))}" if not is_samju else "모름"
        
        yong_data = analysis_result.get('용희기신', {})
        yong = safe_str(yong_data.get('용신', ''))
        hee = safe_str(yong_data.get('희신', ''))
        gi = safe_str(yong_data.get('기신', ''))
        dm_data = analysis_result.get('일간', {})
        
        user_prompt = f"""
[기본] 명식={safe_str(pillars)}; 성별={safe_str(user_data.get('gender'))}; 시간={time_text}; 형태={pillar_type};
[핵심] 일간={safe_str(dm_data.get('글자'))}({safe_str(dm_data.get('오행'))}); 격국={safe_str(analysis_result.get('격국'))}; 신강신약={safe_str(analysis_result.get('신강신약'))}; 조후={safe_str(analysis_result.get('조후'))}; 용신={yong}; 희신={hee}; 기신={gi};
[보조] 오행={w_text}; 십성={sip_text}; 상호작용={inter_text};
[운세] 대운={safe_str(daeun_info.get('방향', ''))}({safe_str(daeun_info.get('대운수', ''))}),흐름={safe_str(daeun_info.get('대운흐름', ''))}; 세운={safe_str(seun_pillar_info[0])}년({safe_str(seun_pillar_info[2])});
"""
        response = model.generate_content(user_prompt)
        text = getattr(response, "text", "")
        return text if isinstance(text, str) and text.strip() else "빈 응답 반환"
    except Exception:
        return "통신 오류 또는 텍스트 추출 실패"