@ECHO OFF
SET DIR=%~dp0
SET WRAPPER_JAR=%DIR%\.mvn\wrapper\maven-wrapper.jar
SET WRAPPER_PROPERTIES=%DIR%\.mvn\wrapper\maven-wrapper.properties

IF NOT EXIST "%WRAPPER_JAR%" (
  ECHO Missing Maven wrapper jar: %WRAPPER_JAR%
  EXIT /B 1
)

IF NOT EXIST "%WRAPPER_PROPERTIES%" (
  ECHO Missing Maven wrapper properties: %WRAPPER_PROPERTIES%
  EXIT /B 1
)

java -Dmaven.multiModuleProjectDirectory=%DIR% -cp "%WRAPPER_JAR%" org.apache.maven.wrapper.MavenWrapperMain %*
