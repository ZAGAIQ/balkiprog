import sympy as sp

def format_equation(force_var, terms_list):
    # Убираем нулевые значения
    terms_list = [sp.sympify(t) for t in terms_list if t != 0 and t != sp.sympify(0)]
    
    if not terms_list:
        print(f"{force_var} = 0")
        return sp.sympify(0)
        
    # Формируем первоначальное уравнение: Силы приравнены к нулю
    lhs_str = force_var
    for t in terms_list:
        term_str = str(t).replace(' ', '')
        if term_str.startswith('-'):
            lhs_str += f" - {term_str[1:]}"
        else:
            lhs_str += f" + {term_str}"
            
    print(f"{lhs_str} = 0")
    
    # Переносим всё в правую часть (меняем знаки)
    rhs_str = ""
    for t in terms_list:
        inv_t = sp.simplify(-t)
        term_str = str(inv_t).replace(' ', '')
        if term_str.startswith('-'):
            rhs_str += f" - {term_str[1:]}"
        else:
            if rhs_str == "":
                rhs_str += f"{term_str}"
            else:
                rhs_str += f" + {term_str}"
                
    if rhs_str == "":
        rhs_str = "0"
        
    print(f"{force_var} = {rhs_str}")
    
    # Полностью сокращаем / упрощаем выражение
    simplified = sp.simplify(sum([-t for t in terms_list]))
    print(f"{force_var} = {simplified}")
    
    return simplified

def main():
    print("=========================================================")
    print("          ПРОГРАММА ДЛЯ РАСЧЕТА ЭПЮР (Nx, Qy, Mz)        ")
    print("=========================================================")
    print("ВАЖНО: Номера узлов и стержней ВСЕГДА идут слева направо (от 1).")
    print("---------------------------------------------------------")
    
    import configparser
    
    print("Как вы хотите ввести данные?")
    print("  1 - Вручную через консоль")
    print("  2 - Считать из файла (task.txt)")
    mode = input("Ваш выбор (по умолчанию 1): ").strip()
    
    plot_vars = {}
    
    if mode == '2':
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
            
            bars_data = {}
            for i in range(1, num_bars + 1):
                sec = f'Bar {i}'
                bars_data[i] = {
                    'L': sp.sympify(config.get(sec, 'L', fallback='0')),
                    'qx': sp.sympify(config.get(sec, 'qx', fallback='0')),
                    'qy': sp.sympify(config.get(sec, 'qy', fallback='0'))
                }
                
            nodes_data = {}
            for i in range(1, num_bars + 2):
                sec = f'Node {i}'
                nodes_data[i] = {
                    'Fx': sp.sympify(config.get(sec, 'Fx', fallback='0')),
                    'Fy': sp.sympify(config.get(sec, 'Fy', fallback='0')),
                    'Mz': sp.sympify(config.get(sec, 'Mz', fallback='0'))
                }
                
            if 'Plot' in config:
                for key, val in config.items('Plot'):
                    plot_vars[sp.Symbol(key)] = float(val)
                    
            print(f"Данные успешно считаны из {filename}!")
            
        except Exception as e:
            print(f"Ошибка при парсинге файла: {e}")
            return
            
    else:
        try:
            base_pos = int(input("Где находится основание (заделка)?\n  1 - Слева (узел 1)\n  2 - Справа (последний узел)\nВаш выбор: "))
            if base_pos not in [1, 2]:
                print("Ошибка: введите 1 или 2.")
                return
                
            num_bars = int(input("Введите количество стержней: "))
            
            # Определяем строку-подсказку для оси X
            if base_pos == 1:
                x_dir_str = "(влево +, вправо -)"
            else:
                x_dir_str = "(вправо +, влево -)"
                
        except ValueError:
            print("Ошибка: введите корректное число.")
            return
    
        bars_data = {}
        print("\n--- Ввод данных для стержней ---")
        for i in range(1, num_bars + 1):
            print(f"\nСтержень {i}:")
            L_str = input("  Длина стержня [L]: ")
            qx_str = input(f"  qx [q] {x_dir_str}: ")
            qy_str = input("  qy [q] (вверх +, вниз -): ")
            
            bars_data[i] = {
                'L': sp.sympify(L_str if L_str else '0'),
                'qx': sp.sympify(qx_str if qx_str else '0'),
                'qy': sp.sympify(qy_str if qy_str else '0')
            }
    
        nodes_data = {}
        print("\n--- Ввод данных для узлов ---")
        for i in range(1, num_bars + 2):
            print(f"\nУзел {i}:")
            Fx_str = input(f"  Fx [qL] {x_dir_str}: ")
            Fy_str = input("  Fy [qL] (вверх +, вниз -): ")
            Mz_str = input("  Момент Mz [qL^2] (по часовой +, против -): ")
            
            nodes_data[i] = {
                'Fx': sp.sympify(Fx_str if Fx_str else '0'),
                'Fy': sp.sympify(Fy_str if Fy_str else '0'),
                'Mz': sp.sympify(Mz_str if Mz_str else '0')
            }

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
                # Момент = Fy * (X_cut - X_force)
                # Дает плюс (по часовой), если сила Fy > 0 действует:
                # - слева от сечения (если идем слева направо, рассматриваем левую часть, X_cut > X_k) -> X_cut - X_k > 0 -> ПЛЮС
                # - справа от сечения (если идем справа налево, рассматриваем правую часть, X_cut < X_k) -> но тогда момент против часовой -> X_cut - X_k < 0 -> МИНУС
                mz_terms.append(sp.simplify(nd['Fy'] * (X_cut - X_k)))
                
            if nd['Mz'] != 0:
                # Момент берем с плюсом по часовой стрелке
                mz_terms.append(nd['Mz'])
                
        # 2. Собираем силы от уже полностью пройденных стержней
        bars_to_consider = range(num_bars, bar_idx, -1) if base_pos == 1 else range(1, bar_idx)
        for k in bars_to_consider:
            bd = bars_data[k]
            L_k = bd['L']
            X_start_k = X_global[k] # Начало по X
            X_center_k = sp.simplify(X_start_k + L_k / 2) # Центр тяжести 
            
            if bd['qx'] != 0:
                nx_terms.append(sp.simplify(bd['qx'] * L_k))
                
            if bd['qy'] != 0:
                qy_terms.append(sp.simplify(bd['qy'] * L_k))
                mz_terms.append(sp.simplify((bd['qy'] * L_k) * (X_cut - X_center_k)))
                
        # 3. Собираем силы от текущего (рассматриваемого) участка от начала до x
        if qx != 0:
            nx_terms.append(sp.simplify(qx * x))
            
        if qy != 0:
            qy_terms.append(sp.simplify(qy * x))
            # Центр тяжести рассматриваемого куска
            if base_pos == 1:
                # Идем в минус по X. Центр тяжести правее сечения на x/2.
                X_center_cut = sp.simplify(X_start - x / 2)
            else:
                # Идем в плюс по X. Центр тяжести левее сечения на x/2.
                X_center_cut = sp.simplify(X_start + x / 2)
                
            mz_terms.append(sp.simplify((qy * x) * (X_cut - X_center_cut)))
        
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
        print(f"Nx(0) = {nx_0}")
        print(f"Nx({L}) = {nx_L}")
        
        print(f"\n--- Рассчет Qy для участка {bar_idx} ---")
        q_expr = format_equation("Qy", qy_terms)
        q_0 = sp.simplify(q_expr.subs(x, 0))
        q_L = sp.simplify(q_expr.subs(x, L))
        print(f"Qy(0) = {q_0}")
        print(f"Qy({L}) = {q_L}")
        
        print(f"\n--- Рассчет Mz для участка {bar_idx} ---")
        mz_expr = format_equation("Mz", mz_terms)
        mz_0 = sp.simplify(mz_expr.subs(x, 0))
        mz_L = sp.simplify(mz_expr.subs(x, L))
        print(f"Mz(0) = {mz_0}")
        print(f"Mz({L}) = {mz_L}")
        
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
        
        plot_epures(results, base_pos, X_global, num_bars, bars_data, x, plot_vars)
        
    except ImportError:
        print("\n[!] Библиотеки matplotlib и/или numpy не установлены. Визуализация не построена.")
        print("Для работы графиков установите их: pip install matplotlib numpy")

def plot_epures(results, base_pos, X_global, num_bars, bars_data, x_sym, predefined_subs=None):
    if predefined_subs is None:
        predefined_subs = {}
        
    import matplotlib.pyplot as plt
    import numpy as np

    free_syms = set()
    for res in results:
        for ex in res['exprs'].values():
            if isinstance(ex, sp.Basic):
                free_syms.update(ex.free_symbols)
        L = bars_data[res['bar']]['L']
        if isinstance(L, sp.Basic):
            free_syms.update(L.free_symbols)
            
    free_syms.discard(x_sym)
    
    # Удаляем из поиска те, что уже предопределены в task.txt
    for sym in predefined_subs.keys():
        free_syms.discard(sym)
    
    subs_dict = dict(predefined_subs)

    if free_syms:
        print("\n================ ВИЗУАЛИЗАЦИЯ ================")
        print("Для построения графиков обнаружены символьные переменные.")
        print("Пожалуйста, введите их числовые значения:")
        for sym in free_syms:
            while True:
                val = input(f"  {sym} = ")
                try:
                    subs_dict[sym] = float(val)
                    break
                except ValueError:
                    print("  Пожалуйста, введите число (например, 10 или 2.5).")
                    
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
    axs[2].set_xlabel('X (координата)')
    axs[2].set_title('Эпюра изгибающих моментов Mz')
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
