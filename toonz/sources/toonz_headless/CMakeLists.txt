set(CMAKE_AUTOMOC ON)

add_executable(toonz_headless
    main.cpp
)

target_link_libraries(toonz_headless
    Qt5::Core
    Qt5::Gui
    Qt5::Script
    toonzlib
    image
    sound
    -Wl,--no-as-needed
    tnzstdfx
    colorfx
    -Wl,--as-needed
)
