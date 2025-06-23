"""
Configuration et scripts pour les tests de charge.
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# Configuration des tests de charge
LOAD_TEST_CONFIG = {
    "scenarios": {
        "light_load": {
            "users": 10,
            "spawn_rate": 2,
            "duration": "5m",
            "description": "Test de charge légère pour validation"
        },
        "normal_load": {
            "users": 50,
            "spawn_rate": 5,
            "duration": "10m", 
            "description": "Test de charge normale pour usage quotidien"
        },
        "peak_load": {
            "users": 200,
            "spawn_rate": 10,
            "duration": "15m",
            "description": "Test de charge de pointe"
        },
        "stress_test": {
            "users": 500,
            "spawn_rate": 20,
            "duration": "20m",
            "description": "Test de stress pour identifier les limites"
        },
        "endurance_test": {
            "users": 100,
            "spawn_rate": 5,
            "duration": "60m",
            "description": "Test d'endurance pour la stabilité long terme"
        }
    },
    
    "environments": {
        "local": {
            "host": "http://localhost:8000",
            "description": "Environnement de développement local"
        },
        "staging": {
            "host": "https://staging-api.enterprise-rag.com",
            "description": "Environnement de staging"
        },
        "production": {
            "host": "https://api.enterprise-rag.com", 
            "description": "Environnement de production (tests limités)"
        }
    },
    
    "monitoring": {
        "metrics_collection": True,
        "response_time_percentiles": [50, 75, 90, 95, 99],
        "error_threshold": 5.0,  # % d'erreurs acceptable
        "response_time_threshold": 2000,  # ms
        "throughput_threshold": 100  # requêtes/seconde
    },
    
    "reporting": {
        "output_dir": "reports/load_tests",
        "formats": ["html", "json", "csv"],
        "include_charts": True,
        "real_time_dashboard": True
    }
}


def generate_load_test_command(scenario: str, environment: str, extra_args: str = "") -> str:
    """Génère la commande Locust pour un scénario donné."""
    
    if scenario not in LOAD_TEST_CONFIG["scenarios"]:
        raise ValueError(f"Scénario non supporté: {scenario}")
    
    if environment not in LOAD_TEST_CONFIG["environments"]:
        raise ValueError(f"Environnement non supporté: {environment}")
    
    config = LOAD_TEST_CONFIG["scenarios"][scenario]
    env_config = LOAD_TEST_CONFIG["environments"][environment]
    
    # Créer le répertoire de sortie
    output_dir = Path(LOAD_TEST_CONFIG["reporting"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time())
    report_prefix = f"{scenario}_{environment}_{timestamp}"
    
    command = [
        "locust",
        f"--locustfile={Path(__file__).parent}/locustfile.py",
        f"--host={env_config['host']}",
        f"--users={config['users']}",
        f"--spawn-rate={config['spawn_rate']}",
        f"--run-time={config['duration']}",
        "--headless",
        f"--html={output_dir}/{report_prefix}.html",
        f"--csv={output_dir}/{report_prefix}",
        "--csv-full-history",
        "--print-stats",
        "--only-summary"
    ]
    
    if extra_args:
        command.append(extra_args)
    
    return " ".join(command)


def generate_docker_compose_override() -> str:
    """Génère un fichier docker-compose override pour les tests de charge."""
    
    override_config = {
        "version": "3.8",
        "services": {
            "rag-api": {
                "environment": [
                    "ENVIRONMENT=load_testing",
                    "LOG_LEVEL=WARNING",  # Réduire les logs pendant les tests
                    "RATE_LIMIT_ENABLED=false",  # Désactiver le rate limiting
                    "CACHE_TTL=300"  # Cache plus agressif
                ],
                "deploy": {
                    "resources": {
                        "limits": {
                            "memory": "4G",
                            "cpus": "2.0"
                        },
                        "reservations": {
                            "memory": "2G", 
                            "cpus": "1.0"
                        }
                    }
                }
            },
            
            "postgres": {
                "environment": [
                    "POSTGRES_MAX_CONNECTIONS=300",
                    "POSTGRES_SHARED_BUFFERS=256MB",
                    "POSTGRES_EFFECTIVE_CACHE_SIZE=1GB"
                ],
                "deploy": {
                    "resources": {
                        "limits": {
                            "memory": "2G",
                            "cpus": "1.0"
                        }
                    }
                }
            },
            
            "redis": {
                "command": [
                    "redis-server",
                    "--maxmemory", "1gb",
                    "--maxmemory-policy", "allkeys-lru",
                    "--save", "\"\"",  # Désactiver la persistance pendant les tests
                    "--appendonly", "no"
                ],
                "deploy": {
                    "resources": {
                        "limits": {
                            "memory": "1G",
                            "cpus": "0.5"
                        }
                    }
                }
            },
            
            # Service de monitoring spécifique aux tests de charge
            "load-test-monitor": {
                "image": "prom/prometheus:latest",
                "ports": ["9090:9090"],
                "volumes": [
                    "./infrastructure/monitoring/prometheus-loadtest.yml:/etc/prometheus/prometheus.yml"
                ],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--storage.tsdb.path=/prometheus",
                    "--web.console.libraries=/etc/prometheus/console_libraries",
                    "--web.console.templates=/etc/prometheus/consoles",
                    "--storage.tsdb.retention.time=24h",
                    "--web.enable-lifecycle"
                ]
            }
        }
    }
    
    return json.dumps(override_config, indent=2)


def create_monitoring_config() -> str:
    """Crée la configuration Prometheus pour les tests de charge."""
    
    prometheus_config = {
        "global": {
            "scrape_interval": "5s",  # Plus fréquent pour les tests
            "evaluation_interval": "5s"
        },
        
        "scrape_configs": [
            {
                "job_name": "rag-api-loadtest",
                "static_configs": [{"targets": ["rag-api:8000"]}],
                "metrics_path": "/metrics",
                "scrape_interval": "5s"
            },
            {
                "job_name": "postgres-loadtest", 
                "static_configs": [{"targets": ["postgres_exporter:9187"]}],
                "scrape_interval": "10s"
            },
            {
                "job_name": "redis-loadtest",
                "static_configs": [{"targets": ["redis_exporter:9121"]}], 
                "scrape_interval": "10s"
            },
            {
                "job_name": "system-loadtest",
                "static_configs": [{"targets": ["node_exporter:9100"]}],
                "scrape_interval": "5s"
            }
        ],
        
        "rule_files": ["loadtest_alerts.yml"]
    }
    
    return f"# Configuration Prometheus pour tests de charge\n{json.dumps(prometheus_config, indent=2)}"


def create_grafana_dashboard() -> Dict[str, Any]:
    """Crée un dashboard Grafana pour les tests de charge."""
    
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "Load Testing Dashboard - Enterprise RAG",
            "tags": ["load-testing", "performance"],
            "timezone": "browser",
            "refresh": "5s",
            "time": {
                "from": "now-30m",
                "to": "now"
            },
            
            "panels": [
                {
                    "id": 1,
                    "title": "Request Rate",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total[1m])",
                            "legendFormat": "Requests/sec"
                        }
                    ],
                    "yAxes": [
                        {"label": "Requests/sec", "min": 0}
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                
                {
                    "id": 2,
                    "title": "Response Time Percentiles",
                    "type": "graph", 
                    "targets": [
                        {
                            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[1m]))",
                            "legendFormat": "50th percentile"
                        },
                        {
                            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m]))",
                            "legendFormat": "95th percentile"
                        },
                        {
                            "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[1m]))", 
                            "legendFormat": "99th percentile"
                        }
                    ],
                    "yAxes": [
                        {"label": "Seconds", "min": 0}
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                
                {
                    "id": 3,
                    "title": "Error Rate",
                    "type": "singlestat",
                    "targets": [
                        {
                            "expr": "rate(http_requests_total{status=~\"5..\"}[1m]) / rate(http_requests_total[1m]) * 100",
                            "legendFormat": "Error Rate %"
                        }
                    ],
                    "thresholds": "1,5",
                    "colorBackground": True,
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 8}
                },
                
                {
                    "id": 4,
                    "title": "Active Users",
                    "type": "singlestat",
                    "targets": [
                        {
                            "expr": "locust_users",
                            "legendFormat": "Users"
                        }
                    ],
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 8}
                },
                
                {
                    "id": 5,
                    "title": "Database Connections",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "pg_stat_database_numbackends",
                            "legendFormat": "Active connections"
                        }
                    ],
                    "gridPos": {"h": 6, "w": 12, "x": 0, "y": 12}
                },
                
                {
                    "id": 6,
                    "title": "Memory Usage",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "process_resident_memory_bytes / 1024 / 1024",
                            "legendFormat": "RSS Memory (MB)"
                        },
                        {
                            "expr": "process_virtual_memory_bytes / 1024 / 1024",
                            "legendFormat": "Virtual Memory (MB)"
                        }
                    ],
                    "gridPos": {"h": 6, "w": 12, "x": 12, "y": 12}
                }
            ]
        }
    }
    
    return dashboard


def create_test_plan(scenario: str) -> Dict[str, Any]:
    """Crée un plan de test détaillé pour un scénario."""
    
    base_plan = {
        "scenario": scenario,
        "created_at": time.time(),
        "config": LOAD_TEST_CONFIG["scenarios"].get(scenario, {}),
        
        "test_phases": [
            {
                "phase": "ramp_up",
                "duration": "2m",
                "description": "Montée en charge progressive"
            },
            {
                "phase": "steady_state", 
                "duration": "5m",
                "description": "Charge constante"
            },
            {
                "phase": "ramp_down",
                "duration": "1m", 
                "description": "Diminution progressive de la charge"
            }
        ],
        
        "success_criteria": {
            "max_error_rate": LOAD_TEST_CONFIG["monitoring"]["error_threshold"],
            "max_response_time_p95": LOAD_TEST_CONFIG["monitoring"]["response_time_threshold"],
            "min_throughput": LOAD_TEST_CONFIG["monitoring"]["throughput_threshold"],
            "system_stability": True
        },
        
        "monitoring_points": [
            "API response times",
            "Database query performance", 
            "Memory usage",
            "CPU utilization",
            "Queue lengths",
            "Error rates",
            "Throughput"
        ]
    }
    
    # Personnalisation par scénario
    if scenario == "stress_test":
        base_plan["success_criteria"]["max_error_rate"] = 10.0  # Plus tolérant
        base_plan["success_criteria"]["max_response_time_p95"] = 5000  # 5 secondes
        base_plan["success_criteria"]["system_stability"] = False  # Peut être instable
        
    elif scenario == "endurance_test":
        base_plan["test_phases"] = [
            {"phase": "ramp_up", "duration": "5m", "description": "Montée en charge progressive"},
            {"phase": "steady_state", "duration": "50m", "description": "Charge constante long terme"},
            {"phase": "ramp_down", "duration": "5m", "description": "Diminution progressive"}
        ]
        base_plan["monitoring_points"].extend([
            "Memory leaks detection",
            "Connection pool exhaustion",
            "Long-term stability metrics"
        ])
    
    return base_plan


# Scripts utilitaires pour l'exécution des tests

BASH_SCRIPTS = {
    "run_load_test.sh": '''#!/bin/bash
# Script d'exécution des tests de charge

set -e

SCENARIO=${1:-"normal_load"}
ENVIRONMENT=${2:-"local"}
EXTRA_ARGS=${3:-""}

echo "🚀 Démarrage du test de charge: $SCENARIO sur $ENVIRONMENT"

# Vérifier que les services sont démarrés
echo "📋 Vérification de l'état des services..."
docker-compose ps

# Démarrer le monitoring si nécessaire
echo "📊 Configuration du monitoring..."
docker-compose -f docker-compose.yml -f docker-compose.loadtest.yml up -d load-test-monitor

# Attendre que les services soient prêts
echo "⏳ Attente de la disponibilité des services..."
sleep 30

# Lancer le test de charge
echo "🔥 Lancement du test de charge..."
python3 -c "
from tests.load.config import generate_load_test_command
cmd = generate_load_test_command('$SCENARIO', '$ENVIRONMENT', '$EXTRA_ARGS')
import os
os.system(cmd)
"

echo "✅ Test de charge terminé!"
echo "📈 Rapports disponibles dans: reports/load_tests/"
''',

    "setup_load_test_env.sh": '''#!/bin/bash
# Script de configuration de l'environnement de test de charge

set -e

echo "🔧 Configuration de l'environnement de test de charge..."

# Installer les dépendances
echo "📦 Installation des dépendances..."
pip install locust faker pytest-benchmark

# Créer les répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p reports/load_tests
mkdir -p infrastructure/monitoring

# Générer les fichiers de configuration
echo "⚙️ Génération des configurations..."
python3 -c "
from tests.load.config import generate_docker_compose_override, create_monitoring_config
import os

# Docker Compose override
with open('docker-compose.loadtest.yml', 'w') as f:
    f.write(generate_docker_compose_override())

# Configuration Prometheus pour tests de charge  
os.makedirs('infrastructure/monitoring', exist_ok=True)
with open('infrastructure/monitoring/prometheus-loadtest.yml', 'w') as f:
    f.write(create_monitoring_config())
"

echo "✅ Environnement configuré!"
echo "💡 Utilisez './run_load_test.sh [scenario] [environment]' pour lancer un test"
''',

    "analyze_results.sh": '''#!/bin/bash
# Script d'analyse des résultats de tests de charge

set -e

RESULTS_DIR=${1:-"reports/load_tests"}

echo "📊 Analyse des résultats de tests de charge..."

# Vérifier que le répertoire existe
if [ ! -d "$RESULTS_DIR" ]; then
    echo "❌ Répertoire de résultats non trouvé: $RESULTS_DIR"
    exit 1
fi

# Lister les rapports disponibles
echo "📋 Rapports disponibles:"
ls -la "$RESULTS_DIR"/*.html 2>/dev/null || echo "Aucun rapport HTML trouvé"

# Générer un résumé
echo "📈 Génération du résumé..."
python3 -c "
import json
import csv
import glob
import os
from pathlib import Path

results_dir = '$RESULTS_DIR'
summary = {'total_tests': 0, 'successful_tests': 0, 'failed_tests': 0}

# Analyser les fichiers CSV
csv_files = glob.glob(f'{results_dir}/*_stats.csv')
for csv_file in csv_files:
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                summary['total_tests'] += 1
                if float(row.get('Failure %', 0)) < 5.0:
                    summary['successful_tests'] += 1
                else:
                    summary['failed_tests'] += 1
    except Exception as e:
        print(f'Erreur lors de l'analyse de {csv_file}: {e}')

print('🎯 Résumé des tests:')
print(f'  Total: {summary[\"total_tests\"]}')
print(f'  Réussis: {summary[\"successful_tests\"]}')  
print(f'  Échoués: {summary[\"failed_tests\"]}')

if summary['total_tests'] > 0:
    success_rate = (summary['successful_tests'] / summary['total_tests']) * 100
    print(f'  Taux de réussite: {success_rate:.1f}%')
"

echo "✅ Analyse terminée!"
'''
}


def create_bash_scripts():
    """Crée les scripts bash pour l'exécution des tests."""
    
    scripts_dir = Path("scripts/load_testing")
    scripts_dir.mkdir(parents=True, exist_ok=True)
    
    for script_name, script_content in BASH_SCRIPTS.items():
        script_path = scripts_dir / script_name
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Rendre le script exécutable
        os.chmod(script_path, 0o755)
    
    print(f"✅ Scripts créés dans {scripts_dir}")


if __name__ == "__main__":
    # Exemple d'utilisation
    import sys
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "generate-command":
            scenario = sys.argv[2] if len(sys.argv) > 2 else "normal_load"
            environment = sys.argv[3] if len(sys.argv) > 3 else "local"
            print(generate_load_test_command(scenario, environment))
            
        elif action == "create-scripts":
            create_bash_scripts()
            
        elif action == "create-config":
            print(generate_docker_compose_override())
            
        else:
            print(f"Action non reconnue: {action}")
            print("Actions disponibles: generate-command, create-scripts, create-config")
    else:
        print("Configuration des tests de charge - Enterprise RAG System")
        print("Scénarios disponibles:", list(LOAD_TEST_CONFIG["scenarios"].keys()))
        print("Environnements disponibles:", list(LOAD_TEST_CONFIG["environments"].keys()))
