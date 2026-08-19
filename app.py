import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq
from lp_solver import solve_periodic_purchasing
from ga_solver import RCPSP_GA
import time
import json

# --- پیکربندی داشبورد ---
st.set_page_config(page_title="مدیریت کلان‌پروژه مسکونی", page_icon="🏢", layout="wide")

# --- مدیریت State برای اتصال تب‌ها و چت‌بات ---
if 'lp_results' not in st.session_state:
    st.session_state.lp_results = None
if 'ga_results' not in st.session_state:
    st.session_state.ga_results = None

# استایل‌های CSS سفارشی برای زیبایی بیشتر
st.markdown("""
    <style>
    .stApp { background-color: #0f172a; }
    .title-box {background-color: #1e293b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; border: 1px solid #334155;}
    .title-text {color: #60a5fa; font-family: 'Tahoma'; font-weight: 800;}
    .stProgress .st-bo {background-color: #0f52ba;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-box"><h1 class="title-text">🏢 سیستم هوشمند مدیریت کلان‌پروژه ساختمانی</h1><p>طراحی شده بر اساس مسائل بهینه‌سازی LP و NP-Hard</p></div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💰 فاز ۱: تخصیص منابع مالی (LP/MILP)", "🏗️ فاز ۲: زمان‌بندی منابع (RCPSP-GA)", "🤖 فاز ۳: چت‌بات مدیر پروژه"])

# ==========================================
# داده‌های مسئله
# ==========================================
PERIODS = [1, 2, 3] 
MATERIALS = {
    'بتن': {'cost': 120, 'demand': 5000, 'progress_weight': 10},
    'میلگرد': {'cost': 850, 'demand': 1200, 'progress_weight': 15},
    'آجر': {'cost': 80, 'demand': 3000, 'progress_weight': 5}
}

TASKS = {
    'تجهیز کارگاه': {'duration': 5, 'preds': [], 'crane': 0, 'crew': 1, 'form': 0},
    'گودبرداری': {'duration': 15, 'preds': ['تجهیز کارگاه'], 'crane': 0, 'crew': 2, 'form': 0},
    'فونداسیون': {'duration': 20, 'preds': ['گودبرداری'], 'crane': 1, 'crew': 3, 'form': 5},
    'اسکلت طبقات': {'duration': 35, 'preds': ['فونداسیون'], 'crane': 2, 'crew': 4, 'form': 8},
    'سفت‌کاری': {'duration': 25, 'preds': ['اسکلت طبقات'], 'crane': 1, 'crew': 2, 'form': 0}
}
RESOURCE_LIMITS = {'Cranes': 2, 'Crews': 5, 'Formworks': 10} 

# ==========================================
# تب ۱: مسئله خطی LP/MILP
# ==========================================
with tab1:
    st.header("بهینه‌سازی خرید دوره‌ای جهت حداکثرسازی سرعت پیشرفت")
    st.write("سیستم با توجه به بودجه هر دوره، تصمیم می‌گیرد چه مقدار از هر مصالح را بخرد تا سرعت پروژه (با وزن‌دهی به خریدهای زودهنگام) ماکزیمم شود.")
    
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        b1 = col1.number_input("بودجه دوره ۱ (دلار)", value=1000000)
        b2 = col2.number_input("بودجه دوره ۲ (دلار)", value=500000)
        b3 = col3.number_input("بودجه دوره ۳ (دلار)", value=300000)
    
    if st.button("📊 حل مسئله تخصیص مالی", use_container_width=True, type="primary"):
        with st.spinner('در حال حل مدل خطی...'):
            time.sleep(0.8) 
            result = solve_periodic_purchasing(MATERIALS, PERIODS, {1: b1, 2: b2, 3: b3})
            
            if result['status'] == 'Optimal':
                st.session_state.lp_results = result # ذخیره برای چت‌بات
                st.success("✅ تخصیص بهینه یافت شد!")
                
                # KPI Cards
                st.markdown("### 📊 شاخص‌های کلیدی عملکرد")
                k1, k2 = st.columns(2)
                k1.metric("کل بودجه در دسترس", f"${b1+b2+b3:,.0f}")
                k2.metric("امتیاز سرعت پیشرفت (تابع هدف Z)", f"{result['score']:,.2f}")
                
                df = pd.DataFrame(result['allocation']).T
                
                st.divider()
                st.markdown("**حجم خرید هر نوع مصالح در دوره‌های مختلف**")
                st.bar_chart(df)
                
                st.markdown("**جدول تفکیکی تخصیص مصالح**")
                st.dataframe(df.style.highlight_max(axis=1, color='#2563eb'), use_container_width=True)
            else:
                st.error("❌ بودجه برای تامین کل مصالح کافی نیست! بودجه را افزایش دهید.")

# ==========================================
# تب ۲: مسئله NP-Hard (GA)
# ==========================================
with tab2:
    st.header("زمان‌بندی با محدودیت منابع (RCPSP)")
    st.write("الگوریتم ژنتیک با در نظر گرفتن محدودیت **جرثقیل، اکیپ و قالب‌ها** بهترین توالی اجرا را می‌یابد.")
    
    with st.expander("مشاهده محدودیت‌های روزانه ماشین‌آلات"):
        st.json(RESOURCE_LIMITS)

    if st.button("🧬 اجرای الگوریتم ژنتیک (GA)", use_container_width=True, type="primary"):
        progress_text = "در حال تکامل نسل‌ها..."
        my_bar = st.progress(0, text=progress_text)
        
        ga = RCPSP_GA(TASKS, RESOURCE_LIMITS, pop_size=100, generations=50)
        
        for percent_complete in range(100):
            time.sleep(0.01)
            my_bar.progress(percent_complete + 1, text=progress_text)
            
        best_makespan, best_schedule, makespan_history = ga.run()
        
        # ذخیره نتایج در State
        st.session_state.ga_results = {
            'makespan': best_makespan,
            'schedule': best_schedule
        }
        
        my_bar.empty()
        st.success(f"✅ بهترین زمان اتمام پروژه (Makespan): {best_makespan} روز")
        
        # رسم نمودار روند همگرایی GA
        st.markdown("### 📉 روند کاهش زمان اتمام پروژه در طول نسل‌ها")
        st.line_chart(pd.DataFrame(makespan_history, columns=["مدت زمان کل پروژه (روز)"]), color="#10b981")
        
        starts = best_schedule[2]
        df_schedule = pd.DataFrame({
            "نام فعالیت": starts.keys(),
            "روز شروع": starts.values(),
            "روز پایان": best_schedule[3].values()
        }).sort_values(by="روز شروع")
        
        st.markdown("### 📅 جدول زمان‌بندی بهینه کارها")
        st.table(df_schedule.set_index("نام فعالیت"))

# ==========================================
# تب ۳: چت‌بات با استفاده از کلید API رایگان Groq
# ==========================================
with tab3:
    st.header("🤖 دستیار هوشمند مدیر پروژه")
    st.info("این بخش مستقیماً از طریق کلید اختصاصی به مدل‌های فوق‌سریع Groq متصل است.")
    
    
    # ساختن Context سیستم بر اساس خروجی مدل‌ها
    system_prompt = (
        "شما یک مدیر و مشاور ارشد پروژه‌های ساختمانی هستید. "
        "لطفاً به سوال کاربر به زبان فارسی، کوتاه، حرفه‌ای و دقیق پاسخ دهید. "
        f"محدودیت ماشین‌آلات روزانه سازمان به این شرح است: {json.dumps(RESOURCE_LIMITS, ensure_ascii=False)}\n"
    )
    
    if st.session_state.lp_results:
        lp_res = st.session_state.lp_results
        system_prompt += f"- نتایج فاز ۱ (خرید مصالح): تخصیص دوره‌ای به این شکل انجام شد: {json.dumps(lp_res['allocation'], ensure_ascii=False)}\n"
    else:
        system_prompt += "- فاز ۱ (خرید مصالح) هنوز بهینه‌سازی نشده است.\n"
        
    if st.session_state.ga_results:
        ga_res = st.session_state.ga_results
        system_prompt += f"- نتایج فاز ۲ (زمان‌بندی): کل پروژه در {ga_res['makespan']} روز تمام می‌شود. برنامه زمانی: {json.dumps(ga_res['schedule'][2], ensure_ascii=False)}\n"
    else:
        system_prompt += "- فاز ۲ (زمان‌بندی منابع) هنوز اجرا نشده است.\n"

    st.success("💡 ربات هوشمند اکنون از آخرین نتایج بهینه‌سازی منابع مالی و زمان‌بندی پروژه آگاه است.")
    
    user_query = st.text_input("سوال تحلیلی خود را در مورد مدیریت این پروژه مسکونی بپرسید:")
    
    if st.button("ارسال به هوش مصنوعی", type="primary"):
        if not user_query:
            st.warning("⚠️ ابتدا سوال خود را تایپ کنید.")
        else:
            try:
                with st.spinner("دستیار در حال تحلیل داده‌های پروژه..."):
                   client = Groq(api_key=st.secrets["GROQ_API_KEY"], timeout=90.0)
                    
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        model="llama-3.1-8b-instant", 
                        temperature=0.3,
                        max_tokens=800,
                    )
                    
                    response_text = chat_completion.choices[0].message.content
                    st.chat_message("user").write(user_query)
                    st.chat_message("assistant").write(response_text)
                    
            except Exception as e:
                st.error(f"ارور ارتباط با سرور: {e}")
