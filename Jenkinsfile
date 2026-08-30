// Jenkinsfile — pipeline deploy manual (homelab)

pipeline {
    agent any

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        COMPOSE_FILE = 'docker-compose.prod.yml'
        ENV_SOURCE   = '/opt/ai-backend/.env'
        IMAGE        = 'ai-backend-v2:latest'
    }

    stages {
        stage('Checkout') {
            steps {
                // Clone repo PRIVATE — pakai credential "github-creds".
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: '*/master']],
                    extensions: [],
                    userRemoteConfigs: [[
                        url: 'https://github.com/Greezzzz/ai-backend-v2.git'
                    ]]
                ])
            }
        }

        stage('Build image') {
            steps {
                // Build image app (Dockerfile multi-stage uv).
                sh 'docker build -t ${IMAGE} .'
            }
        }

        stage('Deploy') {
            steps {
                // .env produksi tidak ada di git — salin dari host.
                sh 'cp ${ENV_SOURCE} .env'

                // Build ulang container yang pakai image baru, daemon.
                sh 'docker compose -f ${COMPOSE_FILE} up -d'

                // Migrasi DB (idempotent — aman dijalankan tiap deploy).
                sh 'docker compose -f ${COMPOSE_FILE} exec -T app alembic upgrade head'

            }
        }

        stage('Health Check') {
            steps{
                sh '''
                    echo "Waiting for server to be ready..."
                    # Coba sampai 30x, jeda 2s (max ~60s)
                    for i in $(seq 1 30); do
                        if curl -sf http://localhost:8000/health; then
                            echo "Server is running"
                            exit 0
                        fi
                        echo "attempt $i: not ready yet..."
                        sleep 2
                    done
                    echo "Server did not become healthy in time"
                    exit 1
                '''
            }
        }
    }
}
