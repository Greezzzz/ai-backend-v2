pipeline {
    agent any

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        VPS_USER = 'ubuntu'
        VPS_HOST = '43.129.33.101'
        APP_DIR  = '/opt/apps/ai-backend'
        COMPOSE  = 'docker-compose.prod.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    if command -v uv >/dev/null 2>&1; then
                        uv sync --frozen --no-dev
                        uv run pytest tests/unit -q
                    else
                        echo "uv tidak ditemukan — skip test"
                    fi
                '''
            }
        }

        stage('Deploy') {
            steps {
                sshagent(['grz-1-ssh']) {
                    sh '''
                        rsync -avz --delete \\
                            --exclude='.git' \\
                            --exclude='.venv' \\
                            --exclude='.env' \\
                            --exclude='.pytest_cache' \\
                            ./ ${VPS_USER}@${VPS_HOST}:${APP_DIR}/

                        ssh ${VPS_USER}@${VPS_HOST} "
                            cd ${APP_DIR} &&
                            docker compose -f ${COMPOSE} up -d --build &&
                            docker compose -f ${COMPOSE} exec -T app alembic upgrade head
                        "
                    '''
                }
            }
        }

        stage('Health Check') {
            steps {
                sshagent(['grz-1-ssh']) {
                    sh '''
                        # Heredoc single-quoted: remote bash terima script apa adanya,
                        # tidak ada mangling $ oleh shell lokal/Jenkins.
                        ssh ${VPS_USER}@${VPS_HOST} bash -s <<'EOF'
                            echo 'Waiting for server...'
                            for i in $(seq 1 30); do
                                if curl -sf http://localhost:8000/health; then
                                    echo 'Server is running'
                                    exit 0
                                fi
                                echo "attempt $i: not ready yet..."
                                sleep 2
                            done
                            echo 'Server did not become healthy in time'
                            exit 1
EOF
                    '''
                }
            }
        }
    }
}
