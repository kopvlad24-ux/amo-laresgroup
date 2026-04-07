from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='static')
CORS(app)

SUBDOMAIN = 'laresgroup'
BASE = f'https://{SUBDOMAIN}.amocrm.ru'

# Группы по именам сотрудников
GROUPS = {
    'andrey': {
        'label': 'Отдел Андрея',
        'names': [
            'Калашников', 'Берегий', 'Печерикина', 'Сухова',
            'Альхатиб', 'Чубарова', 'Земкина', 'Вахрамеева',
            'Корниенко', 'Ягофарова'
        ]
    },
    'arena': {
        'label': 'Отдел Арена',
        'names': [
            'Кимбер', 'Стыцюк', 'Ваврина', 'Римская',
            'Рогов', 'Колганов', 'Большакова Валерия'
        ]
    },
    'kirill': {
        'label': 'Отдел Кирилла',
        'names': [
            'Терешин', 'Карзинина', 'Ходякова', 'Большакова Галина',
            'Марченкова', 'Эрднеев', 'Разгоняева'
        ]
    }
}

def user_matches_group(user_name, group_key):
    name_lower = user_name.lower()
    for pattern in GROUPS[group_key]['names']:
        parts = pattern.lower().split()
        if all(p in name_lower for p in parts):
            return True
    return False

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/proxy/<path:path>')
def proxy(path):
    token = request.headers.get('X-Token')
    if not token:
        return jsonify({'error': 'No token'}), 401
    params = dict(request.args)
    try:
        r = requests.get(
            f'{BASE}/api/v4/{path}',
            headers={'Authorization': f'Bearer {token}'},
            params=params,
            timeout=15
        )
        return (r.content, r.status_code, {'Content-Type': 'application/json'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/group_users')
def group_users():
    token = request.headers.get('X-Token')
    if not token:
        return jsonify({'error': 'No token'}), 401

    group_key = request.args.get('group', 'all')

    try:
        r = requests.get(
            f'{BASE}/api/v4/users',
            headers={'Authorization': f'Bearer {token}'},
            params={'limit': 250},
            timeout=15
        )
        users_data = r.json()
        users = users_data.get('_embedded', {}).get('users', [])

        if group_key == 'all':
            all_patterns = []
            for g in GROUPS.values():
                all_patterns.extend(g['names'])
            filtered = [u for u in users if any(
                all(p.lower() in u.get('name','').lower() for p in pattern.lower().split())
                for pattern in all_patterns
            )]
            group_label = 'Все отделы'
        elif group_key in GROUPS:
            filtered = [u for u in users if user_matches_group(u.get('name', ''), group_key)]
            group_label = GROUPS[group_key]['label']
        else:
            return jsonify({'error': 'Unknown group'}), 400

        return jsonify({
            'users': filtered,
            'group_found': True,
            'group_name': group_label,
            'group_key': group_key,
            'count': len(filtered),
            'groups': {k: v['label'] for k, v in GROUPS.items()}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh', methods=['POST'])
def refresh_token():
    data = request.json
    try:
        r = requests.post(f'{BASE}/oauth2/access_token', json={
            'client_id': data['client_id'],
            'client_secret': data['client_secret'],
            'grant_type': 'refresh_token',
            'refresh_token': data['refresh_token'],
            'redirect_uri': 'https://localhost'
        }, timeout=15)
        return (r.content, r.status_code, {'Content-Type': 'application/json'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5057))
    app.run(host='0.0.0.0', port=port)
