import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from datetime import datetime
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import saju_core

class SajuGUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 사주 분석 시스템")
        self.root.geometry("800x700")
        
        input_frame = ttk.LabelFrame(root, text="사주 정보 입력", padding=15)
        input_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(input_frame, text="Gemini API Key:").grid(row=0, column=0, sticky="e", pady=5)
        self.api_entry = ttk.Entry(input_frame, width=50, show="*")
        self.api_entry.grid(row=0, column=1, columnspan=3, sticky="w", pady=5)

        ttk.Label(input_frame, text="양력 생년월일 (YYYY-MM-DD):").grid(row=1, column=0, sticky="e", pady=5)
        self.date_entry = ttk.Entry(input_frame, width=15)
        self.date_entry.grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(input_frame, text="태어난 시간 (HH:MM, 모르면 비움):").grid(row=1, column=2, sticky="e", pady=5)
        self.time_entry = ttk.Entry(input_frame, width=15)
        self.time_entry.grid(row=1, column=3, sticky="w", pady=5)

        ttk.Label(input_frame, text="성별:").grid(row=2, column=0, sticky="e", pady=5)
        self.gender_var = tk.StringVar(value="M")
        gender_combo = ttk.Combobox(input_frame, textvariable=self.gender_var, values=["M", "F"], width=13, state="readonly")
        gender_combo.grid(row=2, column=1, sticky="w", pady=5)

        ttk.Label(input_frame, text="출생 국가/도시 (한국이면 비움):").grid(row=2, column=2, sticky="e", pady=5)
        self.location_entry = ttk.Entry(input_frame, width=15)
        self.location_entry.grid(row=2, column=3, sticky="w", pady=5)

        self.run_btn = ttk.Button(input_frame, text="사주 분석 시작", command=self.start_analysis)
        self.run_btn.grid(row=3, column=0, columnspan=4, pady=15)

        output_frame = ttk.LabelFrame(root, text="AI 분석 결과", padding=10)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.result_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=("맑은 고딕", 10))
        self.result_text.pack(fill="both", expand=True)

        self.geolocator = Nominatim(user_agent="saju_gui_app")
        self.tf = TimezoneFinder()

    def log_msg(self, msg):
        self.root.after(0, lambda: self._append_log(msg))

    def _append_log(self, msg):
        self.result_text.insert(tk.END, msg + "\n")
        self.result_text.see(tk.END)

    def start_analysis(self):
        self.run_btn.config(state="disabled")
        self.result_text.delete(1.0, tk.END)
        self.log_msg("분석을 시작합니다. 잠시만 기다려주세요...\n")
        
        thread = threading.Thread(target=self.run_logic)
        thread.daemon = True
        thread.start()

    def run_logic(self):
        try:
            api_key = self.api_entry.get().strip()
            if not api_key:
                raise ValueError("Gemini API Key를 입력해주세요.")

            date_str = self.date_entry.get().strip()
            try:
                year, month, day = map(int, date_str.split('-'))
                datetime(year, month, day)
            except ValueError:
                raise ValueError("생년월일을 YYYY-MM-DD 형식으로 정확히 입력해주세요. (예: 1990-05-20)")

            time_str = self.time_entry.get().strip()
            hour, minute = None, None
            if time_str:
                try:
                    hour, minute = map(int, time_str.split(':'))
                except ValueError:
                    raise ValueError("시간을 HH:MM 형식으로 정확히 입력해주세요. (예: 14:30)")

            gender = self.gender_var.get()
            city_name = self.location_entry.get().strip()

            timezone_str = "Asia/Seoul"
            longitude = 126.98

            if city_name:
                self.log_msg(f"해외 지역 '{city_name}'의 위경도 및 타임존을 검색 중입니다...")
                try:
                    locations = self.geolocator.geocode(city_name, exactly_one=False, limit=1)
                except Exception:
                    raise ValueError("네트워크 오류 또는 위치 검색 실패입니다. 인터넷 연결을 확인해주세요.")
                
                if not locations:
                    raise ValueError("해당 지역을 찾을 수 없습니다. 영문 도시명을 정확히 입력해주세요.")
                
                loc = locations[0]
                longitude = loc.longitude
                tz = self.tf.timezone_at(lng=loc.longitude, lat=loc.latitude)
                if not tz:
                    tz = self.tf.closest_timezone_at(lng=loc.longitude, lat=loc.latitude)
                if not tz:
                    tz = "UTC"

                timezone_str = tz
                self.log_msg(f"위치 확인됨: {timezone_str} (경도: {longitude:.2f})\n")

            user_data = {
                "year": year, "month": month, "day": day,
                "hour": hour, "minute": minute, "gender": gender,
                "timezone_str": timezone_str, "longitude": longitude
            }

            self.log_msg("명식(사주 팔자)을 추출하는 중...")
            pillars = saju_core.get_accurate_saju(
                year=year, month=month, day=day,
                hour=hour, minute=minute,
                timezone_str=timezone_str, longitude=longitude
            )
            if isinstance(pillars, dict) and "error" in pillars:
                raise ValueError(pillars["error"])

            self.log_msg("대운 및 세운 흐름을 계산하는 중...")
            daeun_info = saju_core.get_daeun_info(
                gender, pillars[0][0], pillars[1], year, month, day, hour, minute, timezone_str
            )
            if isinstance(daeun_info, dict) and "error" in daeun_info:
                raise ValueError(daeun_info["error"])

            seun_pillar_info = saju_core.get_current_seun(timezone_str=timezone_str, longitude=longitude)
            if isinstance(seun_pillar_info, dict) and "error" in seun_pillar_info:
                raise ValueError(seun_pillar_info["error"])

            self.log_msg("사주 오행 분포 및 십성을 분석하는 중...")
            analyzer = saju_core.SajuAnalyzer(pillars)
            analysis_result = analyzer.analyze()

            self.log_msg("AI 마스터가 운세 풀이를 작성하는 중입니다... (약 10~20초 소요)")
            fortune_reading = saju_core.get_gemini_saju_reading(
                pillars, analysis_result, user_data, daeun_info, seun_pillar_info, api_key
            )

            self.log_msg("\n================= [분석 완료] =================")
            self.log_msg(fortune_reading)

        except Exception as e:
            self.log_msg(f"\n[오류 발생] {str(e)}")
        finally:
            self.root.after(0, lambda: self.run_btn.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = SajuGUIApp(root)
    root.mainloop()
