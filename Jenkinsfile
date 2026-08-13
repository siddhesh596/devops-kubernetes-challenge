pipeline {
    agent any

    environment {
        // Windows executable paths
        PYTHON = 'C:\\Users\\siddh\\AppData\\Local\\Programs\\Python\\Python310\\python.exe'
        DOCKER = 'C:\\Users\\siddh\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe'
        KUBECTL = 'C:\\Users\\siddh\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\kubectl.exe'

        // Kubernetes configuration
        KUBECONFIG = 'C:\\Users\\siddh\\.kube\\config'

        // Local Docker registry
        REGISTRY = 'localhost:5001'

        // Application
        IMAGE_NAME = 'devops-kubernetes-app'
        IMAGE_TAG = "${BUILD_NUMBER}"
        FULL_IMAGE = "${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                echo '========================================'
                echo 'Checking out source code'
                echo '========================================'

                checkout scm
            }
        }

        stage('Verify Tools') {
            steps {
                bat '''
                    echo ========================================
                    echo Jenkins User
                    echo ========================================
                    whoami

                    echo ========================================
                    echo Python
                    echo ========================================
                    "%PYTHON%" --version

                    echo ========================================
                    echo Docker
                    echo ========================================
                    "%DOCKER%" --version

                    echo ========================================
                    echo Kubernetes
                    echo ========================================
                    "%KUBECTL%" version --client

                    echo ========================================
                    echo Kubernetes Context
                    echo ========================================
                    "%KUBECTL%" config current-context

                    echo ========================================
                    echo Kubernetes Nodes
                    echo ========================================
                    "%KUBECTL%" get nodes
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '''
                    echo ========================================
                    echo Installing Python dependencies
                    echo ========================================

                    "%PYTHON%" -m pip install --upgrade pip

                    "%PYTHON%" -m pip install -r app\\requirements.txt

                    "%PYTHON%" -m pip install pytest
                '''
            }
        }

        stage('Run Tests') {
            steps {
                bat '''
                    echo ========================================
                    echo Running tests
                    echo ========================================

                    "%PYTHON%" -m pytest tests -v
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                bat '''
                    echo ========================================
                    echo Building Docker image
                    echo ========================================

                    "%DOCKER%" build ^
                        -t "%IMAGE_NAME%:%IMAGE_TAG%" ^
                        .
                '''
            }
        }

        stage('Tag Docker Image') {
            steps {
                bat '''
                    echo ========================================
                    echo Tagging Docker image
                    echo ========================================

                    "%DOCKER%" tag ^
                        "%IMAGE_NAME%:%IMAGE_TAG%" ^
                        "%FULL_IMAGE%"
                '''
            }
        }

        stage('Push Docker Image') {
            steps {
                bat '''
                    echo ========================================
                    echo Pushing image to local registry
                    echo ========================================

                    "%DOCKER%" push "%FULL_IMAGE%"
                '''
            }
        }

        stage('Verify Registry Image') {
            steps {
                bat '''
                    echo ========================================
                    echo Verifying image
                    echo ========================================

                    "%DOCKER%" image inspect "%FULL_IMAGE%"
                '''
            }
        }

        stage('Deploy PostgreSQL') {
            steps {
                bat '''
                    echo ========================================
                    echo Deploying PostgreSQL
                    echo ========================================

                    "%KUBECTL%" apply -f K8s\\namespace.yaml
                    "%KUBECTL%" apply -f K8s\\secret.yaml
                    "%KUBECTL%" apply -f K8s\\postgres.yaml

                    echo Waiting for PostgreSQL...

                    "%KUBECTL%" -n devops rollout status deployment/postgres --timeout=180s
                '''
            }
        }

        stage('Deploy Backend') {
            steps {
                bat '''
                    echo ========================================
                    echo Deploying Backend
                    echo ========================================

                    "%KUBECTL%" apply -f K8s\\backend.yaml

                    echo Updating backend image:

                    "%KUBECTL%" -n devops set image ^
                        deployment/backend ^
                        backend="%FULL_IMAGE%"

                    echo Waiting for backend rollout...

                    "%KUBECTL%" -n devops rollout status ^
                        deployment/backend ^
                        --timeout=180s
                '''
            }
        }

        stage('Verify Kubernetes Deployment') {
            steps {
                bat '''
                    echo ========================================
                    echo Kubernetes Pods
                    echo ========================================

                    "%KUBECTL%" get pods -n devops -o wide

                    echo ========================================
                    echo Kubernetes Deployments
                    echo ========================================

                    "%KUBECTL%" get deployments -n devops

                    echo ========================================
                    echo Kubernetes Services
                    echo ========================================

                    "%KUBECTL%" get services -n devops

                    echo ========================================
                    echo Backend Image
                    echo ========================================

                    "%KUBECTL%" -n devops get deployment backend ^
                        -o jsonpath="{.spec.template.spec.containers[0].image}"

                    echo.
                '''
            }
        }

        stage('Application Health Check') {
            steps {
                bat '''
                    echo ========================================
                    echo Starting temporary port-forward
                    echo ========================================

                    start /B "" "%KUBECTL%" -n devops port-forward service/backend-service 5000:5000 > "%WORKSPACE%\\port-forward.log" 2>&1

                    timeout /T 5 /NOBREAK > NUL

                    echo ========================================
                    echo Health Check
                    echo ========================================

                    curl.exe -f http://localhost:5000/health

                    echo.
                    echo ========================================
                    echo Database Health Check
                    echo ========================================

                    curl.exe -f http://localhost:5000/db-health

                    echo.
                    echo ========================================
                    echo Tasks API
                    echo ========================================

                    curl.exe -f http://localhost:5000/tasks

                    echo.
                    echo ========================================
                    echo Health checks completed
                    echo ========================================
                '''
            }
        }
    }

    post {

        success {
            echo '========================================'
            echo 'CI/CD PIPELINE SUCCESSFUL'
            echo '========================================'

            echo "Build Number: ${BUILD_NUMBER}"
            echo "Docker Image: ${FULL_IMAGE}"
        }

        failure {
            echo '========================================'
            echo 'CI/CD PIPELINE FAILED'
            echo '========================================'

            echo "Build Number: ${BUILD_NUMBER}"
            echo "Check the Jenkins console output."
        }

        always {
            echo '========================================'
            echo 'Pipeline Finished'
            echo '========================================'
        }
    }
}