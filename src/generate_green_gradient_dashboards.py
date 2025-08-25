#!/usr/bin/env python3
"""
Скрипт для генерации единого дашборда Grafana с разными цветовыми градиентами для каждого параметра.
Создает один дашборд со всеми панелями для обычных и предсказанных значений.
Каждый параметр имеет свой цвет: education - зеленый, health - синий, income - красный и т.д.
"""

import json
import os
from typing import Dict, List, Tuple, Any

# Цветовые схемы для разных параметров
COLOR_SCHEMES = {
    'educational': {
        'name': 'Education (Green)',
        'start': (144, 238, 144),  # Светло-зеленый
        'end': (0, 100, 0)         # Темно-зеленый
    },
    'health': {
        'name': 'Health (Blue)', 
        'start': (173, 216, 230),  # Светло-голубой
        'end': (0, 0, 139)         # Темно-синий
    },
    'social': {
        'name': 'Social Security (Red)',
        'start': (255, 182, 193),  # Светло-розовый
        'end': (139, 0, 0)         # Темно-красный
    },
    'housing': {
        'name': 'Housing (Purple)',
        'start': (221, 160, 221),  # Светло-фиолетовый
        'end': (75, 0, 130)        # Индиго
    },
    'food': {
        'name': 'Food Access (Orange)',
        'start': (255, 218, 185),  # Персиковый
        'end': (255, 69, 0)        # Красно-оранжевый
    },
    'income': {
        'name': 'Income (Yellow)',
        'start': (255, 255, 224),  # Светло-желтый
        'end': (184, 134, 11)      # Темно-золотой
    },
    'ext_pov': {
        'name': 'Extreme Poverty (Gray)',
        'start': (211, 211, 211),  # Светло-серый
        'end': (47, 79, 79)        # Темно-серый
    },
    'cohesion': {
        'name': 'Social Cohesion (Pink)',
        'start': (255, 192, 203),  # Розовый
        'end': (199, 21, 133)      # Темно-розовый
    }
}

def get_parameter_color_scheme(parameter: str) -> Dict:
    """Определяет цветовую схему для параметра"""
    param_lower = parameter.lower()
    
    if 'educational' in param_lower or 'education' in param_lower:
        return COLOR_SCHEMES['educational']
    elif 'health' in param_lower:
        return COLOR_SCHEMES['health'] 
    elif 'social' in param_lower and 'security' in param_lower:
        return COLOR_SCHEMES['social']
    elif 'housing' in param_lower:
        return COLOR_SCHEMES['housing']
    elif 'food' in param_lower:
        return COLOR_SCHEMES['food']
    elif 'income' in param_lower:
        return COLOR_SCHEMES['income']
    elif 'ext_pov' in param_lower:
        return COLOR_SCHEMES['ext_pov']
    elif 'cohesion' in param_lower:
        return COLOR_SCHEMES['cohesion']
    else:
        # По умолчанию - зеленый
        return COLOR_SCHEMES['educational']

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
                parameters[key].append(float(value))
    
    return parameters

def generate_color_gradient(values: List[float], color_scheme: Dict) -> List[Tuple[float, str]]:
    """Генерирует градиент для указанной цветовой схемы"""
    if not values:
        return []
    
    unique_values = sorted(set(values))
    num_colors = len(unique_values)
    
    start_color = color_scheme['start']
    end_color = color_scheme['end']
    
    colors = []
    
    for i, value in enumerate(unique_values):
        # Интерполяция между цветами (от светлого к темному)
        ratio = i / (num_colors - 1) if num_colors > 1 else 0
        
        r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
        
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        colors.append((value, color_hex))
    
    return colors

def create_color_rules(parameter: str, values: List[float]) -> List[Dict]:
    """Создает правила цветов для каждого уникального значения"""
    if not values:
        return []
    
    color_scheme = get_parameter_color_scheme(parameter)
    colors = generate_color_gradient(values, color_scheme)
    rules = []
    
    for value, color in colors:
        rule = {
            "check": {
                "operation": "eq",
                "property": parameter,
                "value": value
            },
            "style": {
                "color": {
                    "fixed": color
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
        }
        rules.append(rule)
    
    return rules

def create_geomap_panel(parameter: str, values: List[float], panel_id: int, 
                       x_pos: int, y_pos: int, width: int = 12, height: int = 8, 
                       hide_tooltip: bool = False) -> Dict:
    """Создает панель geomap для параметра"""
    color_rules = create_color_rules(parameter, values)
    color_scheme = get_parameter_color_scheme(parameter)
    
    # Добавляем название цветовой схемы к заголовку
    title = parameter.replace('_', ' ').title() + f" ({color_scheme['name']})"
    
    panel = {
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
                        "tooltip": hide_tooltip,  # Управляем отображением tooltip
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
            "overrides": [
                {
                    "matcher": {
                        "id": "byRegexp",
                        "options": "(?!.*(" + parameter.replace('value_', '').replace('_', '|') + "))"
                    },
                    "properties": [
                        {
                            "id": "custom.hideFrom",
                            "value": {
                                "tooltip": True,
                                "legend": False,
                                "viz": False
                            }
                        }
                    ]
                }
            ] if not hide_tooltip else []
        },
        "gridPos": {
            "h": height,
            "w": width,
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
                    "src": "public/maps/mexico_states_with_all_values_and_nowcasts.geojson",
                    "tooltip": not hide_tooltip,  # Управляем tooltip для слоя
                    "type": "geojson"
                }
            ],
            "tooltip": {
                "mode": "none" if hide_tooltip else "single"  # Настройка режима tooltip
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
        "title": title,
        "type": "geomap"
    }
    
    return panel

def create_single_dashboard(parameters: Dict[str, List[float]], 
                          title: str = "Mexico Poverty Indicators - Complete Dashboard",
                          hide_tooltip: bool = True) -> Dict:
    """Создает единый дашборд со всеми панелями"""
    
    # Разделяем параметры на обычные и предсказанные
    regular_params = {k: v for k, v in parameters.items() if not k.endswith('_predicted')}
    predicted_params = {k: v for k, v in parameters.items() if k.endswith('_predicted')}
    
    panels = []
    panel_id = 1
    
    # Создаем панели для обычных значений
    y_pos = 0
    for i, (param, values) in enumerate(regular_params.items()):
        x_pos = (i % 2) * 12  # 2 панели в ряду
        if i > 0 and i % 2 == 0:
            y_pos += 8
        
        panel = create_geomap_panel(param, values, panel_id, x_pos, y_pos, 12, 8, hide_tooltip)
        panels.append(panel)
        panel_id += 1
    
    # Добавляем разделитель между обычными и предсказанными значениями
    if regular_params:
        y_pos += 8
        
        # Добавляем текстовую панель-разделитель
        separator_panel = {
            "datasource": {
                "type": "grafana-testdata-datasource",
                "uid": "PD8C576611E62080A"
            },
            "fieldConfig": {
                "defaults": {},
                "overrides": []
            },
            "gridPos": {
                "h": 2,
                "w": 24,
                "x": 0,
                "y": y_pos
            },
            "id": panel_id,
            "options": {
                "code": {
                    "language": "plaintext",
                    "showLineNumbers": False,
                    "showMiniMap": False
                },
                "content": "## Predicted Values",
                "mode": "markdown"
            },
            "pluginVersion": "10.0.0",
            "title": "Predicted Values Section",
            "type": "text"
        }
        panels.append(separator_panel)
        panel_id += 1
        y_pos += 2
    
    # Создаем панели для предсказанных значений
    predicted_start_idx = 0
    for i, (param, values) in enumerate(predicted_params.items()):
        x_pos = (i % 2) * 12  # 2 панели в ряду
        if i > 0 and i % 2 == 0:
            y_pos += 8
        
        panel = create_geomap_panel(param, values, panel_id, x_pos, y_pos, 12, 8, hide_tooltip)
        panels.append(panel)
        panel_id += 1
    
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
        "id": None,
        "links": [],
        "liveNow": False,
        "panels": panels,
        "refresh": "",
        "schemaVersion": 38,
        "style": "dark",
        "tags": ["poverty", "mexico", "geospatial"],
        "templating": {
            "list": []
        },
        "time": {
            "from": "now-6h",
            "to": "now"
        },
        "timepicker": {},
        "timezone": "",
        "title": title,
        "uid": "mexico_complete_dashboard",
        "version": 1,
        "weekStart": ""
    }
    
    return dashboard

def main():
    """Основная функция"""
    # Загружаем данные
    geojson_file = "src/official_data_mexico_states.geojson"
    
    if not os.path.exists(geojson_file):
        print(f"Файл {geojson_file} не найден!")
        return
    
    data = load_geojson_data(geojson_file)
    parameters = extract_parameters_and_values(data)
    
    print(f"Найдено параметров: {len(parameters)}")
    for param, values in parameters.items():
        print(f"  {param}: {len(values)} значений")
    
    # Создаем единый дашборд (по умолчанию скрываем лишние поля в tooltip)
    dashboard = create_single_dashboard(parameters, hide_tooltip=True)
    
    # Сохраняем дашборд
    output_dir = "src/grafana_dashboards"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "mexico_complete_dashboard.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    
    print(f"\nДашборд сохранен: {output_file}")
    print(f"Общее количество панелей: {len(dashboard['panels'])}")

if __name__ == "__main__":
    main() 