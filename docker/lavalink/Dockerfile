FROM openjdk:10-jre-slim

WORKDIR /opt/Lavalink

COPY Lavalink.jar .

# For regular use, doesn't override lib search path
ENTRYPOINT ["java", "-Xmx1G", "-jar", "Lavalink.jar"]

# For sedmelluq/lavaplayer#137
#COPY libs/ /opt/Lavalink/libs/
#ENTRYPOINT ["java", "-Xmx1G", "-Dlavaplayer.native.dir=/opt/Lavalink/libs", "-jar", "Lavalink.jar"]
