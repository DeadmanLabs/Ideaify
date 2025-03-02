FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/usr/local/lib/python3.8/dist-packages:/opt/pjproject/pjsip-apps/src/python
ENV LD_LIBRARY_PATH=/usr/local/lib
RUN echo "tzdata tzdata/Areas select America" | debconf-set-selections && \
    echo "tzdata tzdata/Zones/America select Toronto" | debconf-set-selections

RUN apt-get update && apt-get install -y tzdata && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update -y 
RUN apt-get install -y build-essential
RUN apt-get install -y git
RUN apt-get install -y pkg-config
RUN apt-get install -y automake
RUN apt-get install -y autoconf
RUN apt-get install -y libtool
RUN apt-get install -y libssl-dev
RUN apt-get install -y libsdl2-dev
RUN apt-get install -y libasound2-dev
RUN apt-get install -y libpulse-dev
RUN apt-get install -y libx11-dev
RUN apt-get install -y libxext-dev
RUN apt-get install -y libxrandr-dev
RUN apt-get install -y libxcursor-dev
RUN apt-get install -y libxi-dev
RUN apt-get install -y ffmpeg
RUN apt-get install -y cmake
RUN apt-get install -y python3-dev
RUN apt-get install -y python3-pip
RUN apt-get install -y python3 swig g++
RUN apt-get install -y kmod
RUN rm -rf /var/apt/list/*

WORKDIR /opt
RUN git clone https://github.com/pjsip/pjproject.git
WORKDIR /opt/pjproject
RUN ./configure --disable-video --enable-shared
RUN make dep && make
RUN make install
WORKDIR /opt/pjproject/pjsip-apps/src/swig
RUN make python
WORKDIR /opt/pjproject/pjsip-apps/src/swig/python
RUN swig -I../../../../pjlib/include -I../../../../pjlib-util/include \
         -I../../../../pjmedia/include -I../../../../pjsip/include \
         -I../../../../pjnath/include -c++ -threads -python -o pjsua2_wrap.cpp ../pjsua2.i
RUN python3 setup.py build
RUN python3 setup.py install
RUN ldconfig
RUN python3 -c "import pjsua2; print('pjsua2 successfully installed')"

WORKDIR /opt
RUN git clone https://github.com/ggerganov/whisper.cpp.git
WORKDIR /opt/whisper.cpp
RUN grep -l "target_link_libraries" examples/*/CMakeLists.txt | xargs sed -i 's/target_link_libraries(\(.*\))/target_link_libraries(\1 dl)/'
RUN echo 'find_library(DL_LIBRARY dl REQUIRED)' >> CMakeLists.txt && \
    sed -i '/^add_subdirectory(examples)/i link_libraries(${DL_LIBRARY})' CMakeLists.txt

RUN make

RUN modprobe snd-dummy
RUN aplay -l

WORKDIR /app
EXPOSE 8000
VOLUME ["/data"]

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "export PYTHONPATH=/usr/local/lib/python3.8/dist-packages:/opt/pjproject/pjsip-apps/src/python && export LD_LIBRARY_PATH=/usr/local/lib:/opt/pjproject/pjsip-apps/src/python && python3 voip_server.py & python3 app.py"]
