import pulp

def solve_periodic_purchasing(materials, periods, budgets):
    # تعریف مسئله: حداکثرسازی سرعت پیشرفت
    prob = pulp.LpProblem("Maximize_Progress_Speed", pulp.LpMaximize)
    
    # متغیرهای تصمیم: مقدار خرید هر ماده در هر دوره
    # x[m, t] = مقدار ماده m در دوره t
    keys = [(m, t) for m in materials.keys() for t in periods]
    x = pulp.LpVariable.dicts("Buy", keys, lowBound=0, cat='Continuous')
    
    # تابع هدف: خریدهای زودهنگام وزن بیشتری در پیشرفت دارند (تقسیم بر شماره دوره)
    objective = []
    for m, data in materials.items():
        for t in periods:
            # هرچه کالا زودتر خریده شود (t کوچکتر)، تاثیر آن در سرعت پروژه بیشتر است
            speed_factor = data['progress_weight'] / t
            objective.append(speed_factor * x[(m, t)])
    prob += pulp.lpSum(objective), "Total_Progress_Speed"
    
    # قید 1: تامین کامل نیاز کل پروژه برای هر مصالح
    for m, data in materials.items():
        prob += pulp.lpSum([x[(m, t)] for t in periods]) == data['demand'], f"Demand_{m}"
        
    # قید 2: محدودیت منابع مالی (بودجه) در هر دوره
    for t in periods:
        prob += pulp.lpSum([materials[m]['cost'] * x[(m, t)] for m in materials.keys()]) <= budgets[t], f"Budget_Period_{t}"
        
    # حل مسئله
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        allocation = {
            m: {f"دوره {t}": x[(m, t)].varValue for t in periods}
            for m in materials.keys()
        }
        return {"status": "Optimal", "score": pulp.value(prob.objective), "allocation": allocation}
    else:
        return {"status": pulp.LpStatus[prob.status], "score": 0, "allocation": {}}