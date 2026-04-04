import sympy as sp

def nice_format(expr):
    s = str(expr)
    s = s.replace('**', '^')
    s = s.replace('*', ' * ')
    return s

def apply_unit(expr_str, unit_expr):
    if not expr_str:
        return sp.sympify(0)
    expr = sp.sympify(expr_str)
    if expr == 0:
        return sp.sympify(0)
    # Если это просто число (нет символов), домножаем на символьную базу
    if not expr.free_symbols:
        return sp.expand(expr * unit_expr)
    return expr

def format_equation(force_var, terms_list):
    # Убираем нулевые значения
    terms_list = [sp.sympify(t) for t in terms_list if t != 0 and t != sp.sympify(0)]
    
    if not terms_list:
        print(f"{force_var}(x) = 0")
        return sp.sympify(0)
        
    # Формируем первоначальное уравнение: Силы приравнены к нулю
    lhs_str = force_var
    for t in terms_list:
        term_str = nice_format(t)
        if term_str.startswith('-'):
            lhs_str += f" - {term_str[1:].strip()}"
        else:
            lhs_str += f" + {term_str}"
            
    print(f"{lhs_str} = 0")
    
    # Переносим всё в правую часть (меняем знаки и раскрываем скобки)
    rhs_str = ""
    for t in terms_list:
        inv_t = sp.expand(-t)
        term_str = nice_format(inv_t)
        if term_str.startswith('-'):
            rhs_str += f" - {term_str[1:].strip()}"
        else:
            if rhs_str == "":
                rhs_str += f"{term_str}"
            else:
                rhs_str += f" + {term_str}"
                
    if rhs_str == "":
        rhs_str = "0"
        
    print(f"{force_var}(x) = {rhs_str}")
    
    # Полностью сокращаем / упрощаем выражение
    simplified = sp.simplify(sum([-t for t in terms_list]))
    
    # Не печатаем третий раз если упрощенное выражение совпадает с rhs_str
    if nice_format(simplified) != rhs_str:
        print(f"{force_var}(x) = {nice_format(simplified)}")
    
    return simplified

def main():
    print("=========================================================")
    print("          ПРОГРАММА ДЛЯ РАСЧЕТА ЭПЮР (Nx, Qy, Mz)        ")
    print("=========================================================")
    print("ВАЖНО: Номера узлов и стержней ВСЕГДА идут слева направо (от 1).")
    print("---------------------------------------------------------")
    
    import configparser
    
    print("Ввод данных производится только из конфигурационного файла.")
    filename = input("Имя файла (нажмите Enter для task.txt): ").strip()
    if not filename: filename = 'task.txt'
    
    config = configparser.ConfigParser()
    config.optionxform = str # Сохраняем регистр ключей
    try:
        if not config.read(filename, encoding='utf-8'):
            print(f"Ошибка: не удалось прочитать файл {filename}")
            return
            
        base_pos = int(config.get('General', 'base', fallback=1))
        num_bars = int(config.get('General', 'bars', fallback=0))
        
        q_sym = sp.Symbol('q')
        L_sym = sp.Symbol('L')
        
        bars_data = {}
        for i in range(1, num_bars + 1):
            sec = f'Bar {i}'
            qx_val = apply_unit(config.get(sec, 'qx', fallback='0'), q_sym)
            if base_pos == 1:
                qx_val = -qx_val
            bars_data[i] = {
                'L': apply_unit(config.get(sec, 'L', fallback='0'), L_sym),
                'qx': qx_val,
                'qy': apply_unit(config.get(sec, 'qy', fallback='0'), q_sym)
            }
            
        nodes_data = {}
        for i in range(1, num_bars + 2):
            sec = f'Node {i}'
            Fx_val = apply_unit(config.get(sec, 'Fx', fallback='0'), q_sym * L_sym)
            if base_pos == 1:
                Fx_val = -Fx_val
            nodes_data[i] = {
                'Fx': Fx_val,
                'Fy': apply_unit(config.get(sec, 'Fy', fallback='0'), q_sym * L_sym),
                'Mz': apply_unit(config.get(sec, 'Mz', fallback='0'), q_sym * (L_sym**2))
            }
            
        if 'Plot' in config:
            print("Секция [Plot] замечена, но она больше не нужна. Все переменные приравниваются к 1.")
                
        print(f"Данные успешно считаны из {filename}!")
        
    except Exception as e:
        print(f"Ошибка при парсинге файла: {e}")
        return

    x = sp.Symbol('x')

    # Глобальные координаты по оси X отсчитываем слева направо (X=0 на Первом узле)
    X_global = {1: sp.sympify(0)}
    for i in range(1, num_bars + 1):
        X_global[i+1] = sp.simplify(X_global[i] + bars_data[i]['L'])

    results = []

    # Определяем порядок прохода стержней
    # Если основание слева (1), мы идем от свободного конца (справа) к основанию (влево)
    # Если основание справа (2), мы идем от свободного конца (слева) к основанию (вправо)
    if base_pos == 1:
        bars_range = range(num_bars, 0, -1)
    else:
        bars_range = range(1, num_bars + 1)

    for bar_idx in bars_range:
        L = bars_data[bar_idx]['L']
        qx = bars_data[bar_idx]['qx']
        qy = bars_data[bar_idx]['qy']
        
        if base_pos == 1: # Идем справа налево
            node_idx = bar_idx + 1  # Узел начала участка (на свободном конце)
            X_start = X_global[node_idx]
            X_cut = sp.simplify(X_start - x) # x растет, X_cut уменьшается
        else: # Идем слева направо
            node_idx = bar_idx      # Узел начала участка (на свободном конце)
            X_start = X_global[node_idx]
            X_cut = sp.simplify(X_start + x) # x растет, X_cut увеличивается
        
        nx_terms = []
        qy_terms = []
        mz_terms = []
        
        # 1. Собираем силы от пройденных узлов
        nodes_to_consider = range(num_bars + 1, bar_idx, -1) if base_pos == 1 else range(1, bar_idx + 1)
        for k in nodes_to_consider:
            nd = nodes_data[k]
            X_k = X_global[k]
            
            if nd['Fx'] != 0:
                nx_terms.append(nd['Fx'])
                
            if nd['Fy'] != 0:
                qy_terms.append(nd['Fy'])
                dist = sp.simplify(X_cut - X_k)
                mz_terms.append(nd['Fy'] * dist)
                
            if nd['Mz'] != 0:
                mz_terms.append(nd['Mz'])
                
        # 2. Собираем силы от уже полностью пройденных стержней
        bars_to_consider = range(num_bars, bar_idx, -1) if base_pos == 1 else range(1, bar_idx)
        for k in bars_to_consider:
            bd = bars_data[k]
            L_k = bd['L']
            X_start_k = X_global[k] # Начало по X
            X_center_k = sp.simplify(X_start_k + L_k / 2) # Центр тяжести 
            
            if bd['qx'] != 0:
                nx_terms.append(bd['qx'] * L_k)
                
            if bd['qy'] != 0:
                qy_terms.append(bd['qy'] * L_k)
                dist = sp.simplify(X_cut - X_center_k)
                mz_terms.append((bd['qy'] * L_k) * dist)
                
        # 3. Собираем силы от текущего (рассматриваемого) участка от начала до x
        if qx != 0:
            nx_terms.append(qx * x)
            
        if qy != 0:
            qy_terms.append(qy * x)
            # Центр тяжести рассматриваемого куска
            if base_pos == 1:
                X_center_cut = sp.simplify(X_start - x / 2)
            else:
                X_center_cut = sp.simplify(X_start + x / 2)
                
            dist = sp.simplify(X_cut - X_center_cut)
            mz_terms.append((qy * x) * dist)
        
        if base_pos == 1:
            # Инвертируем знаки для Qy и Mz при заделке слева
            qy_terms = [-t for t in qy_terms]
            mz_terms = [-t for t in mz_terms]

        print(f"\n=========================================================")
        if base_pos == 1:
            print(f"1. Берем участок {bar_idx} (справа налево от узла {bar_idx+1} к узлу {bar_idx})")
        else:
            print(f"1. Берем участок {bar_idx} (слева направо от узла {bar_idx} к узлу {bar_idx+1})")
        print(f"   Координата x начинается от узла {node_idx}.")
        
        print(f"\n--- Рассчет Nx для участка {bar_idx} ---")
        nx_expr = format_equation("Nx", nx_terms)
        nx_0 = sp.simplify(nx_expr.subs(x, 0))
        nx_L = sp.simplify(nx_expr.subs(x, L))
        print(f"Nx(0) = {nice_format(nx_0)}")
        print(f"Nx({nice_format(L)}) = {nice_format(nx_L)}")
        
        print(f"\n--- Рассчет Qy для участка {bar_idx} ---")
        q_expr = format_equation("Qy", qy_terms)
        q_0 = sp.simplify(q_expr.subs(x, 0))
        q_L = sp.simplify(q_expr.subs(x, L))
        print(f"Qy(0) = {nice_format(q_0)}")
        print(f"Qy({nice_format(L)}) = {nice_format(q_L)}")
        
        print(f"\n--- Рассчет Mz для участка {bar_idx} ---")
        mz_expr = format_equation("Mz", mz_terms)
        mz_0 = sp.simplify(mz_expr.subs(x, 0))
        mz_L = sp.simplify(mz_expr.subs(x, L))
        print(f"Mz(0) = {nice_format(mz_0)}")
        print(f"Mz({nice_format(L)}) = {nice_format(mz_L)}")
        
        # Сохраняем координаты для построения
        results.append({
            'bar': bar_idx,
            'exprs': {'Nx': nx_expr, 'Qy': q_expr, 'Mz': mz_expr},
            'coords': {
                'Nx': [(0, nx_0), (L, nx_L)],
                'Qy': [(0, q_0), (L, q_L)],
                'Mz': [(0, mz_0), (L, mz_L)]
            }
        })

    # Вывод словарей/массивов с координатами
    print("\n=========================================================")
    print("ВЫВОД МАССИВОВ КООРДИНАТ ДЛЯ ПОСТРОЕНИЯ ЭПЮР (СИМВОЛЬНЫХ)")
    for res in results:
        bar = res['bar']
        coords = res['coords']
        print(f"\nУчасток {bar}:")
        print(f"  Координаты Nx: {coords['Nx']}")
        print(f"  Координаты Qy: {coords['Qy']}")
        print(f"  Координаты Mz: {coords['Mz']}")

    # ================= ВИЗУАЛИЗАЦИЯ =================
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        plot_epures(results, base_pos, X_global, num_bars, bars_data, x)
        
    except ImportError:
        print("\n[!] Библиотеки matplotlib и/или numpy не установлены. Визуализация не построена.")
        print("Для работы графиков установите их: pip install matplotlib numpy")

def plot_epures(results, base_pos, X_global, num_bars, bars_data, x_sym):
    import matplotlib.pyplot as plt
    import numpy as np

    q_sym = sp.Symbol('q')
    L_sym = sp.Symbol('L')
    subs_dict = {q_sym: 1.0, L_sym: 1.0}

    # Находим все остальные неизвестные переменные и приравниваем их к 1
    free_syms = set()
    for res in results:
        for ex in res['exprs'].values():
            if isinstance(ex, sp.Basic):
                free_syms.update(ex.free_symbols)
        L = bars_data[res['bar']]['L']
        if isinstance(L, sp.Basic):
            free_syms.update(L.free_symbols)
            
    free_syms.discard(x_sym)
    
    for sym in free_syms:
        if sym not in subs_dict:
            subs_dict[sym] = 1.0
            
    print("\n================ ВИЗУАЛИЗАЦИЯ ================")
    print("Графики строятся с числовыми значениями: q = 1, L = 1")
                    
    X_plot = []
    Nx_plot = []
    Qy_plot = []
    Mz_plot = []
    
    # Генерируем точки всегда слева направо (от стержня 1 до num_bars)
    for bar_idx in range(1, num_bars + 1):
        res = next(r for r in results if r['bar'] == bar_idx)
        L_sym = bars_data[bar_idx]['L']
        L_num = float(L_sym.subs(subs_dict)) if isinstance(L_sym, sp.Basic) else float(L_sym)
        
        if base_pos == 1:
            X_start_sym = X_global[bar_idx + 1]
            X_start_num = float(X_start_sym.subs(subs_dict)) if isinstance(X_start_sym, sp.Basic) else float(X_start_sym)
            local_x_arr = np.linspace(0, L_num, 50)
            X_arr = X_start_num - local_x_arr
        else:
            X_start_sym = X_global[bar_idx]
            X_start_num = float(X_start_sym.subs(subs_dict)) if isinstance(X_start_sym, sp.Basic) else float(X_start_sym)
            local_x_arr = np.linspace(0, L_num, 50)
            X_arr = X_start_num + local_x_arr
            
        nx_num = []
        qy_num = []
        mz_num = []
        
        nx_expr = res['exprs']['Nx'].subs(subs_dict) if isinstance(res['exprs']['Nx'], sp.Basic) else res['exprs']['Nx']
        qy_expr = res['exprs']['Qy'].subs(subs_dict) if isinstance(res['exprs']['Qy'], sp.Basic) else res['exprs']['Qy']
        mz_expr = res['exprs']['Mz'].subs(subs_dict) if isinstance(res['exprs']['Mz'], sp.Basic) else res['exprs']['Mz']
        
        for lx in local_x_arr:
            try:
                nx_num.append(float(nx_expr.subs(x_sym, lx) if isinstance(nx_expr, sp.Basic) else nx_expr))
            except TypeError: nx_num.append(0.0)
                
            try:
                qy_num.append(float(qy_expr.subs(x_sym, lx) if isinstance(qy_expr, sp.Basic) else qy_expr))
            except TypeError: qy_num.append(0.0)
                
            try:
                mz_num.append(float(mz_expr.subs(x_sym, lx) if isinstance(mz_expr, sp.Basic) else mz_expr))
            except TypeError: mz_num.append(0.0)
            
        # сортируем, чтобы линия графика шла слева направо по глобальному X
        sort_idx = np.argsort(X_arr)
        X_plot.extend(np.array(X_arr)[sort_idx])
        Nx_plot.extend(np.array(nx_num)[sort_idx])
        Qy_plot.extend(np.array(qy_num)[sort_idx])
        Mz_plot.extend(np.array(mz_num)[sort_idx])

    fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    
    # Отрисовываем границы стержней
    unique_x = set()
    for i in range(1, num_bars + 2):
        x_val = float(X_global[i].subs(subs_dict)) if isinstance(X_global[i], sp.Basic) else float(X_global[i])
        unique_x.add(x_val)
        
    for ax in axs:
        for x_val in unique_x:
            ax.axvline(x=x_val, color='black', linestyle='--', alpha=0.5)
            
    # Добавляем точки координат по краям
    annotated_points = {0: set(), 1: set(), 2: set()}
    for res in results:
        bar_idx = res['bar']
        coords = res['coords']
        
        if base_pos == 1:
            X_start_sym = X_global[bar_idx + 1]
            X_end_sym = X_global[bar_idx]
        else:
            X_start_sym = X_global[bar_idx]
            X_end_sym = X_global[bar_idx + 1]
            
        X_s = float(X_start_sym.subs(subs_dict)) if isinstance(X_start_sym, sp.Basic) else float(X_start_sym)
        X_e = float(X_end_sym.subs(subs_dict)) if isinstance(X_end_sym, sp.Basic) else float(X_end_sym)
        
        for k, var_name in enumerate(['Nx', 'Qy', 'Mz']):
            val_0_sym = coords[var_name][0][1]
            val_L_sym = coords[var_name][1][1]
            
            y_s = float(val_0_sym.subs(subs_dict)) if isinstance(val_0_sym, sp.Basic) else float(val_0_sym)
            y_e = float(val_L_sym.subs(subs_dict)) if isinstance(val_L_sym, sp.Basic) else float(val_L_sym)
            
            pt_s = (round(X_s, 3), round(y_s, 3))
            if pt_s not in annotated_points[k]:
                axs[k].plot(pt_s[0], pt_s[1], 'ko', markersize=4)
                axs[k].annotate(f"({pt_s[0]:.1f}; {pt_s[1]:.1f})", pt_s, textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
                annotated_points[k].add(pt_s)
                
            pt_e = (round(X_e, 3), round(y_e, 3))
            if pt_e not in annotated_points[k]:
                axs[k].plot(pt_e[0], pt_e[1], 'ko', markersize=4)
                axs[k].annotate(f"({pt_e[0]:.1f}; {pt_e[1]:.1f})", pt_e, textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
                annotated_points[k].add(pt_e)
    
    axs[0].plot(X_plot, Nx_plot, 'b-', linewidth=2)
    axs[0].fill_between(X_plot, Nx_plot, alpha=0.3, color='blue')
    axs[0].set_ylabel('Nx')
    axs[0].grid(True)
    axs[0].set_title('Эпюра продольной силы Nx')
    
    axs[1].plot(X_plot, Qy_plot, 'r-', linewidth=2)
    axs[1].fill_between(X_plot, Qy_plot, alpha=0.3, color='red')
    axs[1].set_ylabel('Qy')
    axs[1].grid(True)
    axs[1].set_title('Эпюра поперечной силы Qy')
    
    axs[2].plot(X_plot, Mz_plot, 'g-', linewidth=2)
    axs[2].fill_between(X_plot, Mz_plot, alpha=0.3, color='green')
    axs[2].set_ylabel('Mz')
    axs[2].grid(True)
    axs[2].set_xlabel('X (длина)')
    axs[2].set_title('Эпюра изгибающих моментов Mz')
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
