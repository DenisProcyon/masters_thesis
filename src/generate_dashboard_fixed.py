#!/usr/bin/env python3
"""
Скрипт для генерации дашборда Grafana с правильной структурой rules.
"""

import json
import os

def load_geojson_data(file_path: str):
    """Загружает данные из GeoJSON файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_parameters_and_values(data):
    """Извлекает все параметры и их значения"""
    parameters = {}
    
    for feature in data['features']:
        properties = feature['properties']
        for key, value in properties.items():
            if key.startswith('value_') and isinstance(value, (int, float)):
                if key not in parameters:
                    parameters[key] = []
                parameters[key].append(value)
    
    return parameters

def generate_color_rules(param_name, values):
    """Создает rules для каждого уникального значения от зеленого до красного"""
    unique_values = sorted(list(set(values)))
    rules = []
    
    if len(unique_values) == 1:
        # Если только одно значение - делаем его зеленым
        rules.append({
            "check": {
                "operation": "eq",
                "property": param_name,
                "value": unique_values[0]
            },
            "style": {
                "color": {"fixed": "#90ee90"},
                "opacity": 0.7,
                "rotation": {"fixed": 0, "max": 360, "min": -360, "mode": "mod"},
                "size": {"fixed": 5, "max": 15, "min": 2},
                "symbol": {"fixed": "img/icons/marker/circle.svg", "mode": "fixed"},
                "symbolAlign": {"horizontal": "center", "vertical": "center"},
                "textConfig": {"fontSize": 12, "offsetX": 0, "offsetY": 0, "textAlign": "center", "textBaseline": "middle"}
            }
        })
        return rules
    
    # Создаем правила для каждого уникального значения
    for i, value in enumerate(unique_values):
        # Рассчитываем позицию в спектре (0 = зеленый, 1 = красный)
        ratio = i / (len(unique_values) - 1) if len(unique_values) > 1 else 0
        
        # Создаем цвет от зеленого до красного
        red = int(144 + (255 - 144) * ratio)      # От 144 до 255
        green = int(238 - (238 - 0) * ratio)      # От 238 до 0
        blue = int(144 - 144 * ratio)             # От 144 до 0
        
        color_hex = f"#{red:02x}{green:02x}{blue:02x}"
        
        rules.append({
            "check": {
                "operation": "eq",
                "property": param_name,
                "value": value
            },
            "style": {
                "color": {"fixed": color_hex},
                "opacity": 0.7,
                "rotation": {"fixed": 0, "max": 360, "min": -360, "mode": "mod"},
                "size": {"fixed": 5, "max": 15, "min": 2},
                "symbol": {"fixed": "img/icons/marker/circle.svg", "mode": "fixed"},
                "symbolAlign": {"horizontal": "center", "vertical": "center"},
                "textConfig": {"fontSize": 12, "offsetX": 0, "offsetY": 0, "textAlign": "center", "textBaseline": "middle"}
            }
        })
    
    return rules

def create_panel_json(parameter_name, is_predicted, color_rules, panel_id, x_pos, y_pos):
    """Создает JSON для панели Grafana"""
    
    # Определяем имя для отображения
    display_name = parameter_name.replace('value_', '').replace('_', ' ').title()
    display_name += " | Official vs Predicted"
    
    panel_json = {
        "datasource": {
            "default": True,
            "type": "yesoreyeram-infinity-datasource",
            "uid": "fentqghis1gxsa"
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                }
            },
            "overrides": []
        },
        "gridPos": {"h": 8, "w": 24, "x": x_pos, "y": y_pos},
        "id": panel_id,
        "options": {
            "basemap": {"config": {}, "name": "Layer 0", "type": "default"},
            "controls": {
                "mouseWheelZoom": True,
                "showAttribution": True,
                "showDebug": False,
                "showMeasure": False,
                "showScale": False,
                "showZoom": True
            },
            "layers": [
                {
                    "config": {"rules": color_rules},
                    "location": {"mode": "geohash"},
                    "name": "Layer 1",
                    "src": "public/maps/mexico_states_with_all_values_and_nowcasts.geojson",
                    "tooltip": True,
                    "type": "geojson"
                }
            ],
            "tooltip": {"mode": "details"},
            "view": {"allLayers": True, "id": "zero", "lat": 23.634501, "lon": -102.552784, "zoom": 5}
        },
        "pluginVersion": "11.2.0",
        "targets": [
            {
                "columns": [],
                "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "fentqghis1gxsa"},
                "filters": [],
                "format": "table",
                "global_query_id": "",
                "parser": "backend",
                "refId": "A",
                "root_selector": "",
                "source": "url",
                "type": "json",
                "url": "",
                "url_options": {"data": "", "method": "GET"}
            }
        ],
        "title": display_name,
        "type": "geomap"
    }
    
    return panel_json

def main():
    """Основная функция"""
    # Путь к GeoJSON файлу
    geojson_file = "src/official_data_mexico_states.geojson"
    
    # Загружаем данные
    print("🔄 Загружаем данные из GeoJSON файла...")
    data = load_geojson_data(geojson_file)
    
    # Извлекаем параметры и значения
    print("📊 Извлекаем параметры и значения...")
    parameters = extract_parameters_and_values(data)
    
    # Разделяем на обычные и predicted параметры
    value_params = {}
    predicted_params = {}
    
    for param_name, values in parameters.items():
        if param_name.endswith('_predicted'):
            predicted_params[param_name] = values
        else:
            value_params[param_name] = values
    
    print(f"✅ Найдено {len(value_params)} обычных параметров и {len(predicted_params)} predicted параметров")
    
    # Создаем панели
    panels = []
    panel_id = 1
    y_position = 0
    
    # Сопоставление параметров
    param_mapping = {
        "value_educational lag": "value_educational_lag_predicted",
        "value_access to health services": "value_health_predicted", 
        "value_access to social security": "value_social_security_predicted",
        "value_housing1": "value_housing_predicted",
        "value_housing2": "value_housing_predicted",
        "value_access to food": "value_food_predicted",
        "value_income": "value_income_predicted",
        "value_ext_pov": "value_social_cohesion_predicted"
    }
    
    # Создаем панели для каждого параметра (объединяем value и predicted в одной панели)
    for param_name, values in value_params.items():
        if not values:
            continue
        
        # Создаем rules для обычных значений
        color_rules = generate_color_rules(param_name, values)
        
        # Добавляем rules для predicted значений в ту же панель
        predicted_param_name = param_mapping.get(param_name)
        if predicted_param_name and predicted_param_name in predicted_params:
            predicted_values = predicted_params[predicted_param_name]
            pred_color_rules = generate_color_rules(predicted_param_name, predicted_values)
            color_rules.extend(pred_color_rules)  # Объединяем rules
        
        # Создаем одну панель с обеими версиями данных (полная ширина)
        panel_combined = create_panel_json(param_name, False, color_rules, panel_id, 0, y_position)
        panels.append(panel_combined)
        panel_id += 1
        
        # Увеличиваем y-позицию для следующей панели
        y_position += 8
    
    # Создаем дашборд
    dashboard = {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": 1,
        "links": [],
        "panels": panels,
        "refresh": "",
        "schemaVersion": 39,
        "style": "dark",
        "tags": ["mexico", "poverty", "predictions", "comparison"],
        "templating": {"list": []},
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {},
        "timezone": "",
        "title": "Mexico States: Value vs Predicted Comparison",
        "uid": "mexico-comparison-dashboard",
        "version": 1,
        "weekStart": ""
    }
    
    # Сохраняем дашборд
    os.makedirs("src/grafana_dashboards", exist_ok=True)
    dashboard_filename = "src/grafana_dashboards/complete_comparison_dashboard.json"
    with open(dashboard_filename, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 ГОТОВО!")
    print(f"✅ Создан дашборд с {len(dashboard['panels'])} панелями")
    print(f"📁 Файл: {dashboard_filename}")
    print(f"🎨 Особенности:")
    
    # Подсчитываем панели по типам
    combined_panels = sum(1 for p in dashboard['panels'] if 'Official vs Predicted' in p['title'])
    
    print(f"   - {combined_panels} панелей (Official vs Predicted в каждой)")
    print(f"   - Правильная структура с rules (как в test.json)")
    print(f"   - Каждое уникальное значение имеет свой цвет")
    print(f"   - Цвета от зеленого (низкие) до красного (высокие)")
    print(f"   - Панели расположены парами для сравнения")

if __name__ == "__main__":
    main() 