    # 运动
    workouts = []
    wp = WORKOUT_DIR / f'HealthAutoExport-{date_str}.json'
    if not wp.exists():
        wp = HEALTH_DIR / f'HealthAutoExport-{date_str}.json'
    if wp.exists():
        wd = json.loads(wp.read_text())
        for w in wd.get('data', []).get('workouts', []):
            timeline = []
            for h in (w.get('heartRateData') or []):
                a = h.get('avg') if h.get('avg') is not None else h.get('Avg')
                m = h.get('max') if h.get('max') is not None else h.get('Max')
                timeline.append({
                    'time': (h.get('date', '')[11:16] if h.get('date') else ''),
                    'avg': float(a) if a is not None else None,
                    'max': float(m) if m is not None else None,
                })

            avgs = [x['avg'] for x in timeline if x.get('avg') is not None]
            mxs = [x['max'] for x in timeline if x.get('max') is not None]
            avg_hr = round(sum(avgs) / len(avgs)) if avgs else None
            max_hr = int(max(mxs)) if mxs else None

            # duration 兼容秒/分钟
            dur_raw = w.get('duration')
            if isinstance(dur_raw, (int, float)):
                duration_min = (dur_raw / 60.0) if dur_raw > 200 else float(dur_raw)
            else:
                duration_min = 0.0

            # 能量兼容数字或对象；源数据通常是 kJ，转换为 kcal
            e = w.get('activeEnergyBurned')
            if isinstance(e, dict):
                qty = e.get('qty') or 0
                unit = (e.get('units') or '').lower()
                energy_kcal = (qty / 4.184) if 'kj' in unit else qty
            else:
                energy_kcal = e or 0

            workouts.append({
                'name': w.get('workoutActivityType') or w.get('name') or '运动',
                'start': (w.get('startDate') or '')[:16].replace('T', ' '),
                'duration_min': duration_min,
                'energy_kcal': float(energy_kcal) if isinstance(energy_kcal, (int, float)) else 0,
                'avg_hr': int(avg_hr) if avg_hr is not None else None,
                'max_hr': int(max_hr) if max_hr is not None else None,
                'hr_timeline': [x for x in timeline if x.get('avg') is not None or x.get('max') is not None]
            })