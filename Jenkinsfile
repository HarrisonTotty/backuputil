/*
 * Builds the `backuputil` utility via PyInstaller for different CentOS versions.
 */

pipeline {
    agent none
    options {
        timestamps()
    }
    stages {
        stage('Build: CentOS 6.9') {
            agent {
                label 'master'
            }
            steps {
                sh '''
                   echo 'Building for CentOS 6.9...'
                   /usr/bin/python2.7 -m PyInstaller backuputil.py --clean -F
                   if [ -d "centos-6.9" ]; then rm -rf "centos-6.9"; fi
                   mv dist centos-6.9
                '''
            }
        }
        stage('Build: CentOS 7.2') {
            agent {
                label 'centos-7.2'
            }
            steps {
                sh '''
                   echo 'Building for CentOS 7.2...'
                   /usr/bin/python2.7 -m PyInstaller backuputil.py --clean -F
                   if [ -d "centos-7.2" ]; then rm -rf "centos-7.2"; fi
                   mv dist centos-7.2
                '''
            }
        }
    }
    post {
        success {
            archiveArtifacts(
                artifacts: 'centos-*/backuputil'
            )
        }
    }
}
