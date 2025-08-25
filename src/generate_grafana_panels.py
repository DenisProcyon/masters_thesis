#!/usr/bin/env python3
"""
Скрипт для генерации панелей Grafana на основе данных из GeoJSON файла.
Создает один дашборд со всеми панелями - value и predicted рядом для сравнения.
Использует правильную структуру с rules как в test.json.
"""

import json
import os
from typing import Dict, List, Tuple, Any

def load_geojson_data(file_path: str) -> Dict:
    """Загружает данные из GeoJSON файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_parameters_and_values(data: Dict) -> Dict[str, List[float]]:
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

def rgb_to_hex(r, g, b):
    """Конвертирует RGB в HEX"""
    return f"#{r:02x}{g:02x}{b:02x}"

def generate_color_rules(param_name: str, values: List[float]) -> List[Dict]:
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
                "color": {
                    "fixed": "#90ee90"
                },
                "opacity": 0.7,
                "rotation": {
                    "fixed": 0,
                    "max": 360,
                    "min": -360,
                    "mode": "mod"
                },
                "size": {
                    "fixed": 5,
                    "max": 15,
                    "min": 2
                },
                "symbol": {
                    "fixed": "img/icons/marker/circle.svg",
                    "mode": "fixed"
                },
                "symbolAlign": {
                    "horizontal": "center",
                    "vertical": "center"
                },
                "textConfig": {
                    "fontSize": 12,
                    "offsetX": 0,
                    "offsetY": 0,
                    "textAlign": "center",
                    "textBaseline": "middle"
                }
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
        
        color_hex = rgb_to_hex(red, green, blue)
        
        rules.append({
            "check": {
                "operation": "eq",
                "property": param_name,
                "value": value
            },
            "style": {
                "color": {
                    "fixed": color_hex
                },
                "opacity": 0.7,
                "rotation": {
                    "fixed": 0,
                    "max": 360,
                    "min": -360,
                    "mode": "mod"
                },
                "size": {
                    "fixed": 5,
                    "max": 15,
                    "min": 2
                },
                "symbol": {
                    "fixed": "img/icons/marker/circle.svg",
                    "mode": "fixed"
                },
                "symbolAlign": {
                    "horizontal": "center",
                    "vertical": "center"
                },
                "textConfig": {
                    "fontSize": 12,
                    "offsetX": 0,
                    "offsetY": 0,
                    "textAlign": "center",
                    "textBaseline": "middle"
                }
            }
        })
    
    return rules

def create_panel_json(
    parameter_name: str,
    is_predicted: bool,
    color_rules: List[Dict],
    panel_id: int,
    x_pos: int,
    y_pos: int
) -> Dict:
    """Создает JSON для панели Grafana"""
    
    # Определяем имя для отображения
    display_name = parameter_name.replace('value_', '').replace('_', ' ').title()
    if is_predicted:
        display_name += " | Predicted"
    else:
        display_name += " | Official"
    
    panel_json = {
        "datasource": {
            "default": True,
            "type": "yesoreyeram-infinity-datasource",
            "uid": "fentqghis1gxsa"
        },
        "fieldConfig": {
            "defaults": {
                "color": {
                    "mode": "thresholds"
                },
                "custom": {
                    "hideFrom": {
                        "legend": False,
                        "tooltip": False,
                        "viz": False
                    }
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {
                            "color": "green",
                            "value": None
                        },
                        {
                            "color": "red",
                            "value": 80
                        }
                    ]
                }
            },
            "overrides": []
        },
        "gridPos": {
            "h": 8,
            "w": 12,
            "x": x_pos,
            "y": y_pos
        },
        "id": panel_id,
        "options": {
            "basemap": {
                "config": {},
                "name": "Layer 0",
                "type": "default"
            },
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
                    "config": {
                        "rules": color_rules
                    },
                    "location": {
                        "mode": "geohash"
                    },
                    "name": "Layer 1",
                    "tooltip": True,
                    "type": "geojson"
                }
            ],
            "tooltip": {
                "mode": "details"
            },
            "view": {
                "allLayers": True,
                "id": "zero",
                "lat": 23.634501,
                "lon": -102.552784,
                "zoom": 5
            }
        },
        "pluginVersion": "11.2.0",
        "targets": [
            {
                "columns": [],
                "datasource": {
                    "type": "yesoreyeram-infinity-datasource",
                    "uid": "fentqghis1gxsa"
                },
                "filters": [],
                "format": "table",
                "global_query_id": "",
                "parser": "backend",
                "refId": "A",
                "root_selector": "",
                "source": "url",
                "type": "json",
                "url": "",
                "url_options": {
                    "data": "",
                    "method": "GET"
                }
            }
        ],
        "title": display_name,
        "type": "geomap"
    }
    
    return panel_json

def generate_complete_dashboard(value_params: Dict, predicted_params: Dict) -> Dict:
    """Создает полный дашборд со всеми панелями"""
    
    panels = []
    panel_id = 1
    y_position = 0
    
    # Создаем словарь для сопоставления обычных и predicted параметров
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
    
    # Создаем панели для каждого параметра (value и predicted рядом)
    for param_name, values in value_params.items():
        if not values:
            continue
            
        # Ищем соответствующий predicted параметр
        predicted_param_name = param_mapping.get(param_name)
        predicted_values = predicted_params.get(predicted_param_name, []) if predicted_param_name else []
        
        # Создаем rules для обычных значений
        color_rules = generate_color_rules(param_name, values)
        
        # Панель для обычных значений (левая позиция)
        panel_value = create_panel_json(
            param_name, False, color_rules, panel_id, 0, y_position
        )
        panels.append(panel_value)
        panel_id += 1
        
        # Панель для predicted значений (правая позиция), если есть данные
        if predicted_values and predicted_param_name:
            pred_color_rules = generate_color_rules(predicted_param_name, predicted_values)
            
            panel_predicted = create_panel_json(
                predicted_param_name, True, pred_color_rules, panel_id, 12, y_position
            )
            panels.append(panel_predicted)
            panel_id += 1
        
        # Увеличиваем y-позицию для следующей пары панелей
        y_position += 8
    
    # Создаем дашборд
    dashboard = {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {
                        "type": "grafana",
                        "uid": "-- Grafana --"
                    },
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        },
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
        "templating": {
            "list": []
        },
        "time": {
            "from": "now-6h",
            "to": "now"
        },
        "timepicker": {},
        "timezone": "",
        "title": "Mexico States: Value vs Predicted Comparison",
        "uid": "mexico-comparison-dashboard",
        "version": 1,
        "weekStart": ""
    }
    
    return dashboard

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
    
    # Выводим информацию о сопоставлении
    print("\n🎨 АНАЛИЗ ЦВЕТОВЫХ ДИАПАЗОНОВ ===")
    for param_name, values in value_params.items():
        if values:
            unique_vals = sorted(list(set(values)))
            predicted_param = param_mapping.get(param_name, "Нет")
            
            print(f"📊 {param_name}")
            print(f"   🟢 Уникальных значений: {len(unique_vals)} (от {min(values):.1f} до {max(values):.1f})")
            
            if predicted_param != "Нет" and predicted_param in predicted_params:
                pred_values = predicted_params[predicted_param]
                pred_unique = sorted(list(set(pred_values)))
                print(f"   🔮 Predicted: {len(pred_unique)} уникальных (от {min(pred_values):.1f} до {max(pred_values):.1f})")
            else:
                print(f"   ❌ Predicted: Нет данных")
            print()
    
    # Создаем полный дашборд
    print("🏗️  Создаем дашборд с правильной структурой (как в test.json)...")
    dashboard = generate_complete_dashboard(value_params, predicted_params)
    
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
    value_panels = sum(1 for p in dashboard['panels'] if 'Official' in p['title'])
    predicted_panels = sum(1 for p in dashboard['panels'] if 'Predicted' in p['title'])
    
    print(f"   - {value_panels} панелей Official")
    print(f"   - {predicted_panels} панелей Predicted")
    print(f"   - Правильная структура с rules (как в test.json)")
    print(f"   - Каждое уникальное значение имеет свой цвет")
    print(f"   - Цвета от зеленого (низкие) до красного (высокие)")
    print(f"   - Панели расположены парами для сравнения")

if __name__ == "__main__":
    main() 