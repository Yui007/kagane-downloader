import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1200
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    title: "Kagane Downloader"
    color: "#1a1a2e"
    
    // Properties
    property int currentScreen: 0  // 0: Browse, 1: Downloads, 2: Settings, 3: About
    property bool isLoading: false
    property bool isDownloading: false
    
    // Download tracking
    property string downloadProgressMsg: ""
    property int downloadCurrent: 0
    property int downloadTotal: 0
    
    // Manga data
    property string mangaTitle: ""
    property string mangaAuthor: ""
    property string mangaDescription: ""
    property string mangaSource: ""
    property string mangaStatus: ""
    property string mangaViews: ""
    property string mangaChapters: ""
    property string mangaCover: ""
    property var mangaGenres: []
    property var chaptersList: []
    
    // Connect to app controller signals
    Connections {
        target: appController
        
        function onMangaLoaded(title, author, description, source, status, views, chapters, cover, genres, chapterNums) {
            mangaTitle = title
            mangaAuthor = author
            mangaDescription = description
            mangaSource = source
            mangaStatus = status
            mangaViews = views
            mangaChapters = chapters
            mangaCover = cover
            mangaGenres = genres
        }
        
        function onChaptersLoaded(chapters) {
            chaptersList = chapters
            chapterModel.clear()
            for (var i = 0; i < chapters.length; i++) {
                chapterModel.append(chapters[i])
            }
        }
        
        function onLoadingStarted() {
            isLoading = true
            statusText.text = "Loading..."
        }
        
        function onLoadingFinished() {
            isLoading = false
            statusText.text = ""
        }
        
        function onLoadingError(error) {
            statusText.text = "Error: " + error
        }
        
        function onLoadingProgress(msg) {
            statusText.text = msg
        }
        
        function onDownloadStarted() {
            isDownloading = true
            downloadProgressMsg = "Starting download..."
            downloadCurrent = 0
            downloadTotal = 0
        }
        
        function onDownloadProgress(current, total, msg) {
            progressBar.value = total > 0 ? current / total : 0
            statusText.text = msg
            downloadProgressMsg = msg
            downloadCurrent = current
            downloadTotal = total
        }
        
        function onDownloadFinished(success, total) {
            isDownloading = false
            statusText.text = "Downloaded " + success + "/" + total + " chapters"
            // Add to history model
            downloadHistoryModel.insert(0, {
                title: mangaTitle,
                success: success,
                total: total,
                time: new Date().toLocaleString(),
                cover: mangaCover
            })
        }
        
        function onDownloadError(error) {
            isDownloading = false
            statusText.text = "Error: " + error
        }
    }
    
    // Chapter list model
    ListModel {
        id: chapterModel
    }
    
    // Download history model
    ListModel {
        id: downloadHistoryModel
    }
    
    // Main layout
    RowLayout {
        anchors.fill: parent
        spacing: 0
        
        // Sidebar
        Rectangle {
            Layout.preferredWidth: 220
            Layout.fillHeight: true
            color: "#16213e"
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 10
                
                // Logo
                Text {
                    text: "🎴 Kagane"
                    font.pixelSize: 24
                    font.bold: true
                    color: "#e94560"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Downloader"
                    font.pixelSize: 14
                    color: "#a0a0a0"
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: 20
                }
                
                // Nav buttons
                Repeater {
                    model: [
                        {icon: "🔍", text: "Browse", screen: 0},
                        {icon: "", text: "Downloads", screen: 1},
                        {icon: "⚙️", text: "Settings", screen: 2},
                        {icon: "ℹ️", text: "About", screen: 3}
                    ]
                    
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        radius: 8
                        color: currentScreen === modelData.screen ? "#e94560" : (navMouseArea.containsMouse ? "#2a3f5f" : "transparent")
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 15
                            spacing: 10
                            
                            Text {
                                text: modelData.icon
                                font.pixelSize: 18
                            }
                            
                            Text {
                                text: modelData.text
                                font.pixelSize: 14
                                color: currentScreen === modelData.screen ? "white" : "#d0d0d0"
                            }
                            
                            Item { Layout.fillWidth: true }
                        }
                        
                        MouseArea {
                            id: navMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: currentScreen = modelData.screen
                        }
                    }
                }
                
                Item { Layout.fillHeight: true }
                
                // Status
                Text {
                    id: statusText
                    text: ""
                    font.pixelSize: 11
                    color: "#a0a0a0"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                
                ProgressBar {
                    id: progressBar
                    Layout.fillWidth: true
                    visible: isDownloading
                    value: 0
                    
                    background: Rectangle {
                        implicitHeight: 6
                        radius: 3
                        color: "#2a3f5f"
                    }
                    
                    contentItem: Item {
                        Rectangle {
                            width: progressBar.visualPosition * parent.width
                            height: parent.height
                            radius: 3
                            color: "#e94560"
                        }
                    }
                }
            }
        }
        
        // Content area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1a1a2e"
            
            // Screen loader
            Loader {
                anchors.fill: parent
                anchors.margins: 20
                sourceComponent: {
                    switch(currentScreen) {
                        case 0: return browseScreen
                        case 1: return downloadsScreen
                        case 2: return settingsScreen
                        case 3: return aboutScreen
                        default: return browseScreen
                    }
                }
            }
        }
    }
    
    // Browse Screen Component
    Component {
        id: browseScreen
        
        ColumnLayout {
            spacing: 15
            
            // URL input row
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                
                TextField {
                    id: urlInput
                    Layout.fillWidth: true
                    placeholderText: "Enter kagane.org manga URL..."
                    font.pixelSize: 14
                    color: "white"
                    
                    background: Rectangle {
                        radius: 8
                        color: "#16213e"
                        border.color: urlInput.focus ? "#e94560" : "#2a3f5f"
                        border.width: 1
                    }
                }
                
                Button {
                    text: isLoading ? "Loading..." : "Fetch"
                    enabled: !isLoading && urlInput.text.length > 0
                    
                    background: Rectangle {
                        radius: 8
                        color: parent.enabled ? (parent.hovered ? "#d63850" : "#e94560") : "#555"
                    }
                    
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 14
                        font.bold: true
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    onClicked: appController.fetchManga(urlInput.text)
                }
            }
            
            // Manga info + chapters
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 15
                visible: mangaTitle !== ""
                
                // Manga info panel
                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    radius: 12
                    color: "#16213e"
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 15
                        spacing: 10
                        
                        // Cover image
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 380
                            radius: 8
                            color: "#2a3f5f"
                            clip: true
                            
                            Image {
                                anchors.fill: parent
                                source: mangaCover
                                fillMode: Image.PreserveAspectCrop
                                visible: mangaCover !== ""
                            }
                            
                            Text {
                                anchors.centerIn: parent
                                text: "📖"
                                font.pixelSize: 60
                                visible: mangaCover === ""
                            }
                        }
                        
                        Text {
                            text: mangaTitle
                            font.pixelSize: 16
                            font.bold: true
                            color: "white"
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        
                        Text {
                            text: "By: " + mangaAuthor
                            font.pixelSize: 12
                            color: "#a0a0a0"
                            visible: mangaAuthor !== ""
                        }
                        
                        Text {
                            text: "Source: " + mangaSource
                            font.pixelSize: 12
                            color: "#a0a0a0"
                            visible: mangaSource !== ""
                        }
                        
                        RowLayout {
                            spacing: 15
                            
                            Text {
                                text: "📊 " + mangaStatus
                                font.pixelSize: 12
                                color: mangaStatus === "ONGOING" ? "#4ade80" : "#fbbf24"
                                visible: mangaStatus !== ""
                            }
                            
                            Text {
                                text: "📚 " + mangaChapters + " ch"
                                font.pixelSize: 12
                                color: "#a0a0a0"
                            }
                            
                            Text {
                                text: "👁 " + mangaViews
                                font.pixelSize: 12
                                color: "#a0a0a0"
                                visible: mangaViews !== ""
                            }
                        }
                        
                        // Genres
                        Flow {
                            Layout.fillWidth: true
                            spacing: 5
                            
                            Repeater {
                                model: mangaGenres
                                
                                Rectangle {
                                    width: genreText.width + 12
                                    height: 22
                                    radius: 11
                                    color: "#2a3f5f"
                                    
                                    Text {
                                        id: genreText
                                        anchors.centerIn: parent
                                        text: modelData
                                        font.pixelSize: 10
                                        color: "#d0d0d0"
                                    }
                                }
                            }
                        }
                        
                        Item { Layout.fillHeight: true }
                    }
                }
                
                // Chapters list
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: "#16213e"
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 15
                        spacing: 10
                        
                        RowLayout {
                            Layout.fillWidth: true
                            
                            Text {
                                text: "Chapters (" + chapterModel.count + ")"
                                font.pixelSize: 16
                                font.bold: true
                                color: "white"
                            }
                            
                            Item { Layout.fillWidth: true }
                            
                            Button {
                                id: invertSortBtn
                                text: "Invert Sort"
                                
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#2a3f5f" : "transparent"
                                    border.color: "#e94560"
                                    border.width: 1
                                }
                                
                                contentItem: Text {
                                    text: parent.text
                                    font.pixelSize: 12
                                    color: "#e94560"
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                
                                onClicked: {
                                    // Collect all items with explicit properties
                                    var items = []
                                    for (var i = 0; i < chapterModel.count; i++) {
                                        var item = chapterModel.get(i)
                                        items.push({
                                            index: item.index,
                                            number: item.number,
                                            title: item.title,
                                            pages: item.pages,
                                            date: item.date,
                                            selected: item.selected
                                        })
                                    }
                                    // Reverse the array
                                    items.reverse()
                                    // Clear and repopulate
                                    chapterModel.clear()
                                    for (var j = 0; j < items.length; j++) {
                                        chapterModel.append(items[j])
                                    }
                                }
                            }
                            
                            Button {
                                property bool allSelected: false
                                text: allSelected ? "Deselect All" : "Select All"
                                
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#2a3f5f" : "transparent"
                                    border.color: "#e94560"
                                    border.width: 1
                                }
                                
                                contentItem: Text {
                                    text: parent.text
                                    font.pixelSize: 12
                                    color: "#e94560"
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                
                                onClicked: {
                                    allSelected = !allSelected
                                    for (var i = 0; i < chapterModel.count; i++) {
                                        chapterModel.setProperty(i, "selected", allSelected)
                                    }
                                }
                            }
                        }
                        
                        // Chapter list
                        ListView {
                            id: chapterListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: chapterModel
                            spacing: 5
                            
                            delegate: Rectangle {
                                width: chapterListView.width
                                height: 45
                                radius: 6
                                color: model.selected ? "#2a3f5f" : "#1a1a2e"
                                border.color: model.selected ? "#e94560" : "transparent"
                                border.width: 1
                                
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    spacing: 10
                                    
                                    CheckBox {
                                        checked: model.selected
                                        onCheckedChanged: chapterModel.setProperty(index, "selected", checked)
                                        
                                        indicator: Rectangle {
                                            implicitWidth: 20
                                            implicitHeight: 20
                                            radius: 4
                                            color: parent.checked ? "#e94560" : "#2a3f5f"
                                            border.color: "#e94560"
                                            
                                            Text {
                                                anchors.centerIn: parent
                                                text: "✓"
                                                color: "white"
                                                visible: parent.parent.checked
                                            }
                                        }
                                    }
                                    
                                    Text {
                                        text: "Ch. " + model.number
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "#e94560"
                                        Layout.preferredWidth: 60
                                    }
                                    
                                    Text {
                                        text: model.title
                                        font.pixelSize: 12
                                        color: "white"
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    
                                    Text {
                                        text: model.pages + " pg"
                                        font.pixelSize: 11
                                        color: "#a0a0a0"
                                    }
                                    
                                    Text {
                                        text: model.date
                                        font.pixelSize: 11
                                        color: "#a0a0a0"
                                    }
                                }
                                
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: chapterModel.setProperty(index, "selected", !model.selected)
                                }
                            }
                        }
                        
                        // Download button
                        Button {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 45
                            text: isDownloading ? "Downloading..." : "Download Selected"
                            enabled: !isDownloading
                            
                            background: Rectangle {
                                radius: 8
                                color: parent.enabled ? (parent.hovered ? "#d63850" : "#e94560") : "#555"
                            }
                            
                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 14
                                font.bold: true
                                color: "white"
                                horizontalAlignment: Text.AlignHCenter
                            }
                            
                            onClicked: {
                                var selected = []
                                for (var i = 0; i < chapterModel.count; i++) {
                                    if (chapterModel.get(i).selected) {
                                        selected.push(i)
                                    }
                                }
                                appController.downloadChapters(selected)
                            }
                        }
                    }
                }
            }
            
            // Empty state
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#16213e"
                visible: mangaTitle === ""
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 15
                    
                    Text {
                        text: "📚"
                        font.pixelSize: 60
                        Layout.alignment: Qt.AlignHCenter
                    }
                    
                    Text {
                        text: "Enter a manga URL to get started"
                        font.pixelSize: 16
                        color: "#a0a0a0"
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }
    
    // Downloads Screen Component
    Component {
        id: downloadsScreen
        
        ColumnLayout {
            spacing: 20
            
            Text {
                text: "Downloads"
                font.pixelSize: 24
                font.bold: true
                color: "white"
            }
            
            // Active Downloads Section
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: isDownloading ? 200 : 80
                radius: 12
                color: "#16213e"
                
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10
                    
                    RowLayout {
                        spacing: 10
                        
                        Text {
                            text: "⚡ Active Download"
                            font.pixelSize: 16
                            font.bold: true
                            color: isDownloading ? "#e94560" : "#a0a0a0"
                        }
                        
                        Rectangle {
                            visible: isDownloading
                            width: 8
                            height: 8
                            radius: 4
                            color: "#4ade80"
                            
                            SequentialAnimation on opacity {
                                running: isDownloading
                                loops: Animation.Infinite
                                NumberAnimation { from: 1.0; to: 0.3; duration: 500 }
                                NumberAnimation { from: 0.3; to: 1.0; duration: 500 }
                            }
                        }
                    }
                    
                    // Download progress content
                    ColumnLayout {
                        visible: isDownloading
                        spacing: 8
                        
                        Text {
                            text: mangaTitle
                            font.pixelSize: 14
                            color: "white"
                            font.bold: true
                        }
                        
                        Text {
                            text: downloadProgressMsg
                            font.pixelSize: 12
                            color: "#a0a0a0"
                        }
                        
                        RowLayout {
                            spacing: 10
                            
                            ProgressBar {
                                id: downloadProgressBar
                                Layout.preferredWidth: 400
                                from: 0
                                to: downloadTotal
                                value: downloadCurrent
                                
                                background: Rectangle {
                                    implicitHeight: 8
                                    radius: 4
                                    color: "#2a3f5f"
                                }
                                
                                contentItem: Item {
                                    Rectangle {
                                        width: downloadProgressBar.visualPosition * parent.width
                                        height: parent.height
                                        radius: 4
                                        color: "#e94560"
                                    }
                                }
                            }
                            
                            Text {
                                text: downloadCurrent + " / " + downloadTotal
                                font.pixelSize: 12
                                color: "#e94560"
                                font.bold: true
                            }
                        }
                        
                        Button {
                            text: "Cancel"
                            
                            background: Rectangle {
                                radius: 6
                                color: parent.hovered ? "#d63850" : "#e94560"
                            }
                            
                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 12
                                color: "white"
                                horizontalAlignment: Text.AlignHCenter
                            }
                            
                            onClicked: appController.stopDownload()
                        }
                    }
                    
                    // No active downloads message
                    Text {
                        visible: !isDownloading
                        text: "No active downloads"
                        font.pixelSize: 14
                        color: "#a0a0a0"
                    }
                }
            }
            
            // Download History Section
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: "#16213e"
                
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10
                    
                    Text {
                        text: "📜 Download History"
                        font.pixelSize: 16
                        font.bold: true
                        color: "white"
                    }
                    
                    ListView {
                        id: historyListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: downloadHistoryModel
                        spacing: 8
                        
                        delegate: Rectangle {
                            width: historyListView.width
                            height: 70
                            radius: 8
                            color: "#1a1a2e"
                            
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 15
                                anchors.rightMargin: 15
                                spacing: 15
                                
                                // Cover thumbnail
                                Rectangle {
                                    width: 50
                                    height: 60
                                    radius: 4
                                    color: "#2a3f5f"
                                    clip: true
                                    
                                    Image {
                                        anchors.fill: parent
                                        source: model.cover || ""
                                        fillMode: Image.PreserveAspectCrop
                                        visible: model.cover !== ""
                                    }
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: "📖"
                                        font.pixelSize: 20
                                        visible: !model.cover || model.cover === ""
                                    }
                                }
                                
                                // Info
                                ColumnLayout {
                                    spacing: 4
                                    
                                    Text {
                                        text: model.title || "Unknown"
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: "white"
                                        elide: Text.ElideRight
                                        Layout.maximumWidth: 400
                                    }
                                    
                                    Text {
                                        text: model.success + " / " + model.total + " chapters"
                                        font.pixelSize: 12
                                        color: model.success === model.total ? "#4ade80" : "#fbbf24"
                                    }
                                    
                                    Text {
                                        text: model.time || ""
                                        font.pixelSize: 11
                                        color: "#a0a0a0"
                                    }
                                }
                                
                                Item { Layout.fillWidth: true }
                                
                                // Status icon
                                Text {
                                    text: model.success === model.total ? "✅" : "⚠️"
                                    font.pixelSize: 20
                                }
                            }
                        }
                        
                        // Empty state
                        Text {
                            anchors.centerIn: parent
                            visible: downloadHistoryModel.count === 0
                            text: "No download history yet"
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                    }
                }
            }
        }
    }
    
    // Settings Screen Component
    Component {
        id: settingsScreen
        
        Rectangle {
            radius: 12
            color: "#16213e"
            
            ScrollView {
                anchors.fill: parent
                anchors.margins: 20
                
                ColumnLayout {
                    width: parent.width
                    spacing: 20
                    
                    Text {
                        text: "Settings"
                        font.pixelSize: 24
                        font.bold: true
                        color: "white"
                    }
                    
                    // Download Format
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: "Download Format"
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        RowLayout {
                            spacing: 10
                            
                            Repeater {
                                model: ["images", "pdf", "cbz"]
                                
                                Rectangle {
                                    width: 80
                                    height: 36
                                    radius: 6
                                    color: settings.downloadFormat === modelData ? "#e94560" : "#2a3f5f"
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.toUpperCase()
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "white"
                                    }
                                    
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: settings.downloadFormat = modelData
                                    }
                                }
                            }
                        }
                    }
                    
                    // Keep Images
                    RowLayout {
                        spacing: 15
                        
                        Text {
                            text: "Keep Images After Conversion"
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        Switch {
                            checked: settings.keepImages
                            onCheckedChanged: settings.keepImages = checked
                        }
                    }
                    
                    // Max Concurrent Chapters
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: "Max Concurrent Chapter Downloads: " + settings.maxConcurrentChapters
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        Slider {
                            from: 1
                            to: 5
                            stepSize: 1
                            value: settings.maxConcurrentChapters
                            onValueChanged: settings.maxConcurrentChapters = value
                            Layout.preferredWidth: 300
                        }
                    }
                    
                    // Max Concurrent Images
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: "Max Concurrent Image Downloads: " + settings.maxConcurrentImages
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        Slider {
                            from: 1
                            to: 10
                            stepSize: 1
                            value: settings.maxConcurrentImages
                            onValueChanged: settings.maxConcurrentImages = value
                            Layout.preferredWidth: 300
                        }
                    }
                    
                    // Image Load Delay
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: "Image Load Delay: " + settings.imageLoadDelay + "s"
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        Slider {
                            from: 5
                            to: 30
                            stepSize: 1
                            value: settings.imageLoadDelay
                            onValueChanged: settings.imageLoadDelay = value
                            Layout.preferredWidth: 300
                        }
                    }
                    
                    // Max Retries
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: "Max Retries: " + settings.maxRetries
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        Slider {
                            from: 1
                            to: 5
                            stepSize: 1
                            value: settings.maxRetries
                            onValueChanged: settings.maxRetries = value
                            Layout.preferredWidth: 300
                        }
                    }
                    
                    // Download Directory
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: "Download Directory"
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        TextField {
                            id: downloadDirField
                            Component.onCompleted: text = settings.downloadDirectory
                            onEditingFinished: settings.downloadDirectory = text
                            Layout.preferredWidth: 400
                            font.pixelSize: 13
                            color: "white"
                            
                            background: Rectangle {
                                radius: 6
                                color: "#1a1a2e"
                                border.color: "#2a3f5f"
                            }
                        }
                    }
                    
                    // Enable Logs
                    RowLayout {
                        spacing: 15
                        
                        Text {
                            text: "Enable Logs"
                            font.pixelSize: 14
                            color: "#a0a0a0"
                        }
                        
                        Switch {
                            checked: settings.enableLogs
                            onCheckedChanged: settings.enableLogs = checked
                        }
                    }
                    
                    Item { height: 20 }
                }
            }
        }
    }
    
    // About Screen Component
    Component {
        id: aboutScreen
        
        Rectangle {
            radius: 12
            color: "#16213e"
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 20
                
                Text {
                    text: "🎴"
                    font.pixelSize: 80
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Kagane Downloader"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#e94560"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Version 1.0.0"
                    font.pixelSize: 14
                    color: "#a0a0a0"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "A beautiful manga downloader for kagane.org"
                    font.pixelSize: 14
                    color: "#d0d0d0"
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Built with PyQt6 + QML"
                    font.pixelSize: 12
                    color: "#a0a0a0"
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
    }
}
