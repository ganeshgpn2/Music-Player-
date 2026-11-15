# Music Player project generator: सबै फाइल यही एउटा फाइलबाट बन्छ (GitHub Actions ले चलाउँछ)
import os
FILES = {
'app/build.gradle.kts': r'''import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val props = Properties().apply {
    val f = rootProject.file("local.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "com.example.musicplayer"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.example.musicplayer"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "YT_API_KEY", "\"${props.getProperty("YOUTUBE_API_KEY", "")}\"")
    }
    buildFeatures { compose = true; buildConfig = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.media3:media3-exoplayer:1.4.1")
    implementation("androidx.media3:media3-session:1.4.1")
    implementation("androidx.media3:media3-ui:1.4.1")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("com.pierfrancescosoffritti.androidyoutubeplayer:core:12.1.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
}
''',
'app/src/main/AndroidManifest.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />

    <application
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:label="Music Player"
        android:supportsRtl="true"
        android:theme="@style/AppTheme">
        <activity android:name=".MainActivity" android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden|smallestScreenSize|screenLayout">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <service android:name=".PlaybackService" android:exported="true"
            android:foregroundServiceType="mediaPlayback">
            <intent-filter>
                <action android:name="androidx.media3.session.MediaSessionService" />
            </intent-filter>
        </service>
        <receiver android:name=".Widget4x1Provider" android:exported="true" android:label="Music Player 4x1">
            <intent-filter><action android:name="android.appwidget.action.APPWIDGET_UPDATE" /></intent-filter>
            <meta-data android:name="android.appwidget.provider" android:resource="@xml/widget_4x1_info" />
        </receiver>
        <receiver android:name=".Widget4x2Provider" android:exported="true" android:label="Music Player 4x2">
            <intent-filter><action android:name="android.appwidget.action.APPWIDGET_UPDATE" /></intent-filter>
            <meta-data android:name="android.appwidget.provider" android:resource="@xml/widget_4x2_info" />
        </receiver>
    </application>
</manifest>
''',
'app/src/main/java/com/example/musicplayer/LocalMedia.kt': r'''package com.example.musicplayer

import android.content.ContentUris
import android.content.Context
import android.provider.MediaStore

/** फोनमा भएका audio (video=false) वा video (video=true) फाइलहरू खोज्छ */
fun loadLocal(ctx: Context, video: Boolean): List<Track> {
    val col = if (video) MediaStore.Video.Media.EXTERNAL_CONTENT_URI
    else MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
    val proj = if (video)
        arrayOf(MediaStore.Video.Media._ID, MediaStore.Video.Media.TITLE)
    else
        arrayOf(
            MediaStore.Audio.Media._ID, MediaStore.Audio.Media.TITLE,
            MediaStore.Audio.Media.ARTIST, MediaStore.Audio.Media.ALBUM_ID
        )
    val sel = if (video) null else "${MediaStore.Audio.Media.IS_MUSIC} != 0"
    val sort = if (video) "${MediaStore.Video.Media.DATE_ADDED} DESC"
    else "${MediaStore.Audio.Media.TITLE} COLLATE NOCASE ASC"

    val out = mutableListOf<Track>()
    ctx.contentResolver.query(col, proj, sel, null, sort)?.use { c ->
        while (c.moveToNext()) {
            val uri = ContentUris.withAppendedId(col, c.getLong(0)).toString()
            val title = c.getString(1) ?: "Unknown"
            out += if (video) Track(uri, title, "", true)
            else {
                val artist = c.getString(2)?.takeIf { it != "<unknown>" } ?: ""
                Track(uri, title, artist, false, "content://media/external/audio/albumart/${c.getLong(3)}")
            }
        }
    }
    return out
}
''',
'app/src/main/java/com/example/musicplayer/MainActivity.kt': r'''package com.example.musicplayer

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.media3.common.C
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlin.math.abs
import kotlin.math.max

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val dark = androidx.compose.foundation.isSystemInDarkTheme()
            MaterialTheme(colorScheme = if (dark) darkColorScheme() else lightColorScheme()) {
                Surface(Modifier.fillMaxSize()) { App() }
            }
        }
    }
}

private fun permissions(): Array<String> =
    if (Build.VERSION.SDK_INT >= 33) arrayOf(
        Manifest.permission.READ_MEDIA_AUDIO, Manifest.permission.READ_MEDIA_VIDEO,
        Manifest.permission.POST_NOTIFICATIONS
    ) else arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)

private fun hasMediaPermission(ctx: Context): Boolean {
    val p = if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO
    else Manifest.permission.READ_EXTERNAL_STORAGE
    return ContextCompat.checkSelfPermission(ctx, p) == PackageManager.PERMISSION_GRANTED
}

private fun toast(ctx: Context, s: String) = Toast.makeText(ctx, s, Toast.LENGTH_SHORT).show()

private fun fmt(ms: Long): String { val s = ms / 1000; return "%d:%02d".format(s / 60, s % 60) }

private fun ago(t: Long): String {
    val m = (System.currentTimeMillis() - t) / 60000
    return when {
        m < 1 -> "अहिले"; m < 60 -> "$m मिनेट अघि"; m < 1440 -> "${m / 60} घण्टा अघि"
        else -> "${m / 1440} दिन अघि"
    }
}

private val TABS = listOf("🎵 गीत", "🎬 भिडियो", "📁 प्लेलिस्ट", "🕘 इतिहास", "🔥 धेरै बजेको", "🆕 नबजेको", "▶ YouTube")

@Composable
fun App() {
    val ctx = LocalContext.current
    var controller by remember { mutableStateOf<MediaController?>(null) }
    var tab by remember { mutableIntStateOf(0) }
    var ytId by remember { mutableStateOf<String?>(null) }
    var playing by remember { mutableStateOf(false) }
    var cur by remember { mutableStateOf<Track?>(null) }
    var isVideo by remember { mutableStateOf(false) }
    var repeat by remember { mutableIntStateOf(0) }
    var shuffle by remember { mutableStateOf(false) }
    var speed by remember { mutableFloatStateOf(1f) }
    var pos by remember { mutableLongStateOf(0L) }
    var dur by remember { mutableLongStateOf(0L) }
    var sleepLeft by remember { mutableLongStateOf(0L) }
    var query by remember { mutableStateOf("") }
    var granted by remember { mutableStateOf(hasMediaPermission(ctx)) }
    var audio by remember { mutableStateOf(emptyList<Track>()) }
    var videos by remember { mutableStateOf(emptyList<Track>()) }
    var stats by remember { mutableStateOf(emptyList<Stat>()) }
    var addTarget by remember { mutableStateOf<Track?>(null) }
    var showSleep by remember { mutableStateOf(false) }

    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        granted = hasMediaPermission(ctx)
    }
    LaunchedEffect(Unit) { if (!granted) launcher.launch(permissions()) }

    // Player सँग जोडिने
    DisposableEffect(Unit) {
        val token = SessionToken(ctx, ComponentName(ctx, PlaybackService::class.java))
        val future = MediaController.Builder(ctx, token).buildAsync()
        future.addListener({ controller = future.get() }, ContextCompat.getMainExecutor(ctx))
        onDispose { MediaController.releaseFuture(future) }
    }
    DisposableEffect(controller) {
        val c = controller
        fun sync(p: Player) {
            playing = p.isPlaying
            cur = p.currentMediaItem?.toTrack()
            isVideo = p.currentTracks.isTypeSelected(C.TRACK_TYPE_VIDEO)
            repeat = p.repeatMode
            shuffle = p.shuffleModeEnabled
            speed = p.playbackParameters.speed
        }
        val l = object : Player.Listener {
            override fun onEvents(p: Player, events: Player.Events) = sync(p)
        }
        if (c != null) { c.addListener(l); sync(c) }
        onDispose { c?.removeListener(l) }
    }
    // Seekbar र sleep timer को बाँकी समय
    LaunchedEffect(controller) {
        while (true) {
            controller?.let { pos = it.currentPosition; dur = it.duration.coerceAtLeast(0L) }
            val end = Store.sleepEnd(ctx)
            val now = System.currentTimeMillis()
            sleepLeft = if (end > now) end - now else 0L
            delay(500)
        }
    }
    LaunchedEffect(granted) {
        if (granted) {
            val a = withContext(Dispatchers.IO) { loadLocal(ctx, false) }
            val v = withContext(Dispatchers.IO) { loadLocal(ctx, true) }
            audio = a; videos = v
        }
    }
    LaunchedEffect(tab, cur) { stats = withContext(Dispatchers.IO) { Store.stats(ctx) } }
    LaunchedEffect(tab) { if (tab == 6) controller?.pause() }

    fun play(list: List<Track>, index: Int, shuf: Boolean?) {
        val c = controller ?: return
        if (list.isEmpty()) return
        shuf?.let { c.shuffleModeEnabled = it }
        c.setMediaItems(list.map { it.toMediaItem() }, index, 0L)
        c.prepare(); c.play(); ytId = null
    }
    fun filt(l: List<Track>) =
        if (query.isBlank()) l else l.filter { it.title.contains(query, true) || it.artist.contains(query, true) }

    Scaffold(bottomBar = {
        val t = cur
        if (t != null && tab != 6) PlayerPanel(
            controller, t, playing, pos, dur, repeat, shuffle, speed, sleepLeft,
            onAdd = { addTarget = t }, onSleep = { showSleep = true }
        )
    }) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            if (isVideo && tab != 6) {
                AndroidView(
                    factory = { PlayerView(it).apply { useController = false } },
                    update = { it.player = controller },
                    modifier = Modifier.fillMaxWidth().aspectRatio(16f / 9f)
                )
            }
            ScrollableTabRow(selectedTabIndex = tab, edgePadding = 8.dp) {
                TABS.forEachIndexed { i, t -> Tab(tab == i, { tab = i }, text = { Text(t) }) }
            }
            if (tab == 0 || tab == 1 || tab == 5) {
                OutlinedTextField(
                    value = query, onValueChange = { query = it }, singleLine = true,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp),
                    placeholder = { Text("🔍 खोज्नुहोस्") }
                )
                if (!granted) {
                    Column(Modifier.padding(16.dp)) {
                        Text("फोनका फाइल हेर्न अनुमति चाहिन्छ।")
                        Button({ launcher.launch(permissions()) }) { Text("अनुमति दिनुहोस्") }
                    }
                }
            }
            Box(Modifier.weight(1f)) {
                when (tab) {
                    0 -> TrackList(filt(audio), onPlay = ::play, onAdd = { addTarget = it })
                    1 -> TrackList(filt(videos), onPlay = ::play, onAdd = { addTarget = it })
                    2 -> PlaylistsTab(addTarget, onPlay = ::play, onAdd = { addTarget = it })
                    3 -> Column {
                        TextButton({ Store.clearStats(ctx); stats = emptyList() }) { Text("🗑 इतिहास/गणना मेटाउने") }
                        val h = stats.sortedByDescending { it.last }.take(100)
                        val m = h.associate { it.track.uri to "${it.track.artist.ifEmpty { "—" }} • ${it.count} बार • ${ago(it.last)}" }
                        TrackList(h.map { it.track }, subtitle = { m[it.uri] ?: "" }, onPlay = ::play, onAdd = { addTarget = it })
                    }
                    4 -> {
                        val h = stats.sortedByDescending { it.count }.take(50)
                        val m = h.associate { it.track.uri to "${it.count} बार बजेको" }
                        TrackList(h.map { it.track }, subtitle = { m[it.uri] ?: "" }, onPlay = ::play, onAdd = { addTarget = it })
                    }
                    5 -> {
                        val played = stats.map { it.track.uri }.toSet()
                        TrackList(filt((audio + videos).filter { it.uri !in played }), onPlay = ::play, onAdd = { addTarget = it })
                    }
                    else -> YouTubeTab(ytId) { ytId = it }
                }
            }
        }
    }

    addTarget?.let { AddToPlaylistDialog(it) { addTarget = null } }
    if (showSleep) SleepDialog { showSleep = false }
}

@Composable
fun Ic(res: Int, tint: Color = LocalContentColor.current, size: Dp = 26.dp, onClick: () -> Unit) {
    IconButton(onClick, Modifier.size(size + 16.dp)) {
        Icon(painterResource(res), null, Modifier.size(size), tint = tint)
    }
}

@Composable
fun PlayerPanel(
    c: MediaController?, cur: Track, playing: Boolean, pos: Long, dur: Long, repeat: Int,
    shuffle: Boolean, speed: Float, sleepLeft: Long, onAdd: () -> Unit, onSleep: () -> Unit
) {
    var drag by remember { mutableStateOf<Float?>(null) }
    val on = MaterialTheme.colorScheme.primary
    val off = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.45f)
    val top = max(dur, 1L).toFloat()
    Surface(tonalElevation = 4.dp) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp)) {
            Text(
                cur.title + if (cur.artist.isNotEmpty()) " • ${cur.artist}" else "",
                maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(fmt(drag?.toLong() ?: pos), style = MaterialTheme.typography.bodySmall)
                Slider(
                    value = (drag ?: pos.toFloat()).coerceIn(0f, top),
                    onValueChange = { drag = it },
                    onValueChangeFinished = { drag?.let { c?.seekTo(it.toLong()) }; drag = null },
                    valueRange = 0f..top, modifier = Modifier.weight(1f).padding(horizontal = 6.dp)
                )
                Text(fmt(dur), style = MaterialTheme.typography.bodySmall)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                Ic(R.drawable.ic_shuffle, if (shuffle) on else off) { c?.shuffleModeEnabled = !shuffle }
                Ic(R.drawable.ic_prev) { c?.seekToPreviousMediaItem() }
                Ic(if (playing) R.drawable.ic_pause else R.drawable.ic_play, size = 38.dp) {
                    c?.let {
                        if (playing) it.pause() else {
                            if (it.playbackState == Player.STATE_IDLE) it.prepare()
                            if (it.playbackState == Player.STATE_ENDED) it.seekToDefaultPosition()
                            it.play()
                        }
                    }
                }
                Ic(R.drawable.ic_stop) { c?.stop(); c?.seekTo(0) }
                Ic(R.drawable.ic_next) { c?.seekToNextMediaItem() }
                Ic(if (repeat == 1) R.drawable.ic_repeat_one else R.drawable.ic_repeat, if (repeat == 0) off else on) {
                    c?.repeatMode = nextRepeat(repeat)
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                TextButton({
                    val s = listOf(0.75f, 1f, 1.25f, 1.5f, 2f)
                    c?.setPlaybackSpeed(s[(s.indexOfFirst { abs(it - speed) < 0.01f } + 1) % s.size])
                }) { Text("⚡ ${speed}x") }
                TextButton(onSleep) {
                    Text(if (sleepLeft > 0) "⏰ ${sleepLeft / 60000 + 1} मि." else "⏰ Sleep")
                }
                TextButton(onAdd) { Text("＋ प्लेलिस्ट") }
            }
            Text(
                when (repeat) { 1 -> "🔂 एउटै दोहोर्‍याउने"; 2 -> "🔁 सबै दोहोर्‍याउने"; else -> "दोहोर्‍याउने छैन" } +
                    " • " + if (shuffle) "🔀 Random" else "क्रमैसँग (Serial)",
                style = MaterialTheme.typography.labelSmall
            )
        }
    }
}

@Composable
fun TrackList(
    tracks: List<Track>,
    subtitle: (Track) -> String = { it.artist },
    showPlayAll: Boolean = true,
    onPlay: (List<Track>, Int, Boolean?) -> Unit,
    onAdd: (Track) -> Unit,
    onRemove: ((Track) -> Unit)? = null
) {
    val ctx = LocalContext.current
    if (tracks.isEmpty()) { Text("कुनै फाइल छैन।", Modifier.padding(16.dp)); return }
    LazyColumn {
        if (showPlayAll) item {
            Row(Modifier.padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button({ onPlay(tracks, 0, false) }) { Text("▶ सबै बजाउने") }
                OutlinedButton({ onPlay(tracks, tracks.indices.random(), true) }) { Text("🔀 Shuffle") }
            }
        }
        itemsIndexed(tracks) { i, t ->
            var menu by remember { mutableStateOf(false) }
            ListItem(
                headlineContent = { Text(t.title, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                supportingContent = { val s = subtitle(t); if (s.isNotEmpty()) Text(s, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                leadingContent = {
                    Box(Modifier.size(44.dp), contentAlignment = Alignment.Center) {
                        Text(if (t.video) "🎬" else "🎵")
                        if (t.art.isNotEmpty()) AsyncImage(t.art, null, Modifier.fillMaxSize())
                    }
                },
                trailingContent = {
                    Box {
                        TextButton({ menu = true }) { Text("⋮") }
                        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(text = { Text("प्लेलिस्टमा थप्ने") }, onClick = { menu = false; onAdd(t) })
                            DropdownMenuItem(text = { Text("❤ मनपर्नेमा थप्ने") }, onClick = {
                                menu = false; Store.add(ctx, Store.FAV, t); toast(ctx, "मनपर्नेमा थपियो")
                            })
                            onRemove?.let { rm ->
                                DropdownMenuItem(text = { Text("यो सूचीबाट हटाउने") }, onClick = { menu = false; rm(t) })
                            }
                        }
                    }
                },
                modifier = Modifier.clickable { onPlay(tracks, i, null) }
            )
            HorizontalDivider()
        }
    }
}

@Composable
fun PlaylistsTab(changed: Track?, onPlay: (List<Track>, Int, Boolean?) -> Unit, onAdd: (Track) -> Unit) {
    val ctx = LocalContext.current
    var refresh by remember { mutableIntStateOf(0) }
    var lists by remember { mutableStateOf(Store.playlists(ctx)) }
    var open by remember { mutableStateOf<String?>(null) }
    var newName by remember { mutableStateOf("") }
    LaunchedEffect(refresh, changed) { lists = Store.playlists(ctx) }

    val o = open
    val tracks = if (o != null) lists[o] else null
    if (o != null && tracks != null) {
        Column(Modifier.fillMaxSize()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton({ open = null }) { Text("← पछाडि") }
                Text(o, Modifier.weight(1f), style = MaterialTheme.typography.titleMedium, maxLines = 1)
                if (o != Store.FAV) TextButton({ Store.delete(ctx, o); open = null; refresh++ }) { Text("🗑 मेट्ने") }
            }
            TrackList(tracks, onPlay = onPlay, onAdd = onAdd, onRemove = { Store.removeFrom(ctx, o, it); refresh++ })
        }
    } else {
        Column(Modifier.fillMaxSize()) {
            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    newName, { newName = it }, Modifier.weight(1f), singleLine = true,
                    placeholder = { Text("नयाँ प्लेलिस्टको नाम") }
                )
                Spacer(Modifier.width(8.dp))
                Button({ Store.create(ctx, newName.trim()); newName = ""; refresh++ }) { Text("＋") }
            }
            LazyColumn {
                items(lists.keys.toList()) { name ->
                    ListItem(
                        headlineContent = { Text(name) },
                        supportingContent = { Text("${lists[name]?.size ?: 0} वटा") },
                        modifier = Modifier.clickable { open = name }
                    )
                    HorizontalDivider()
                }
            }
        }
    }
}

@Composable
fun AddToPlaylistDialog(track: Track, onDismiss: () -> Unit) {
    val ctx = LocalContext.current
    val names = remember { Store.playlists(ctx).keys.toList() }
    var name by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onDismiss) { Text("बन्द") } },
        title = { Text("प्लेलिस्टमा थप्ने") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                names.forEach { n ->
                    TextButton({ Store.add(ctx, n, track); toast(ctx, "$n मा थपियो"); onDismiss() }) { Text(n) }
                }
                OutlinedTextField(name, { name = it }, singleLine = true, placeholder = { Text("नयाँ प्लेलिस्ट") })
                TextButton({
                    if (name.isNotBlank()) { Store.add(ctx, name.trim(), track); toast(ctx, "थपियो"); onDismiss() }
                }) { Text("＋ बनाएर थप्ने") }
            }
        }
    )
}

@Composable
fun SleepDialog(onDismiss: () -> Unit) {
    val ctx = LocalContext.current
    fun set(min: Int) {
        ctx.startService(Intent(ctx, PlaybackService::class.java).setAction(PlaybackService.ACTION_SLEEP).putExtra("min", min))
        toast(ctx, if (min > 0) "$min मिनेटपछि बन्द हुन्छ" else "Sleep timer रद्द")
        onDismiss()
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onDismiss) { Text("बन्द") } },
        title = { Text("⏰ Sleep timer") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                listOf(5, 10, 15, 30, 45, 60, 90).forEach { m -> TextButton({ set(m) }) { Text("$m मिनेट") } }
                TextButton({ set(0) }) { Text("रद्द गर्ने") }
            }
        }
    )
}
''',
'app/src/main/java/com/example/musicplayer/Model.kt': r'''package com.example.musicplayer

import android.content.Context
import android.net.Uri
import android.os.Bundle
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import org.json.JSONArray
import org.json.JSONObject

data class Track(
    val uri: String, val title: String, val artist: String = "",
    val video: Boolean = false, val art: String = ""
)

data class Stat(val track: Track, val count: Int, val last: Long)

fun Track.toMediaItem(): MediaItem = MediaItem.Builder()
    .setUri(Uri.parse(uri)).setMediaId(uri)
    .setMediaMetadata(
        MediaMetadata.Builder().setTitle(title).setArtist(artist)
            .setArtworkUri(if (art.isNotEmpty()) Uri.parse(art) else null)
            .setExtras(Bundle().apply { putBoolean("video", video) }).build()
    ).build()

fun MediaItem.toTrack(): Track? {
    val u = localConfiguration?.uri?.toString() ?: mediaId.ifEmpty { return null }
    val m = mediaMetadata
    return Track(
        u, m.title?.toString() ?: "Unknown", m.artist?.toString() ?: "",
        m.extras?.getBoolean("video") ?: false, m.artworkUri?.toString() ?: ""
    )
}

/** Repeat: 0=Off, 1=One, 2=All. क्रम: Off → All → One → Off */
fun nextRepeat(m: Int) = when (m) { 0 -> 2; 2 -> 1; else -> 0 }

/** इतिहास, गणना, प्लेलिस्ट, sleep समय — सबै फोनमै SharedPreferences मा सुरक्षित */
object Store {
    const val FAV = "❤ मनपर्ने"
    private fun sp(c: Context) = c.getSharedPreferences("store", Context.MODE_PRIVATE)

    private fun Track.json() = JSONObject().put("u", uri).put("t", title).put("a", artist).put("v", video).put("r", art)
    private fun JSONObject.track() = Track(getString("u"), optString("t"), optString("a"), optBoolean("v"), optString("r"))

    // ---- बजेको गणना / इतिहास ----
    @Synchronized fun recordPlay(c: Context, t: Track) {
        val o = JSONObject(sp(c).getString("stats", "{}") ?: "{}")
        val old = o.optJSONObject(t.uri)
        val e = JSONObject().put("k", t.json())
            .put("c", (old?.optInt("c", 0) ?: 0) + 1)
            .put("l", System.currentTimeMillis())
        o.put(t.uri, e)
        sp(c).edit().putString("stats", o.toString()).apply()
    }

    @Synchronized fun stats(c: Context): List<Stat> {
        val o = JSONObject(sp(c).getString("stats", "{}") ?: "{}")
        return o.keys().asSequence().map { k ->
            val e = o.getJSONObject(k)
            Stat(e.getJSONObject("k").track(), e.getInt("c"), e.getLong("l"))
        }.toList()
    }

    @Synchronized fun clearStats(c: Context) { sp(c).edit().remove("stats").apply() }

    // ---- प्लेलिस्ट ----
    @Synchronized fun playlists(c: Context): LinkedHashMap<String, MutableList<Track>> {
        val o = JSONObject(sp(c).getString("lists", "{}") ?: "{}")
        val m = LinkedHashMap<String, MutableList<Track>>()
        m[FAV] = mutableListOf()
        for (k in o.keys()) {
            val a = o.getJSONArray(k)
            m[k] = MutableList(a.length()) { a.getJSONObject(it).track() }
        }
        return m
    }

    private fun save(c: Context, m: Map<String, List<Track>>) {
        val o = JSONObject()
        for ((k, v) in m) o.put(k, JSONArray().also { a -> v.forEach { a.put(it.json()) } })
        sp(c).edit().putString("lists", o.toString()).apply()
    }

    @Synchronized fun create(c: Context, name: String) {
        val m = playlists(c)
        if (name.isNotBlank() && name !in m) { m[name] = mutableListOf(); save(c, m) }
    }
    @Synchronized fun add(c: Context, name: String, t: Track) {
        val m = playlists(c)
        val l = m.getOrPut(name) { mutableListOf() }
        if (l.none { it.uri == t.uri }) l.add(t)
        save(c, m)
    }
    @Synchronized fun removeFrom(c: Context, name: String, t: Track) {
        val m = playlists(c); m[name]?.removeAll { it.uri == t.uri }; save(c, m)
    }
    @Synchronized fun delete(c: Context, name: String) {
        if (name == FAV) return
        val m = playlists(c); m.remove(name); save(c, m)
    }

    // ---- sleep timer ----
    fun sleepEnd(c: Context): Long = sp(c).getLong("sleep_end", 0L)
    fun setSleepEnd(c: Context, v: Long) { sp(c).edit().putLong("sleep_end", v).apply() }
}
''',
'app/src/main/java/com/example/musicplayer/PlaybackService.kt': r'''package com.example.musicplayer

import android.content.Intent
import android.os.Handler
import android.os.Looper
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService

/** Background playback, notification controls, sleep timer, इतिहास रेकर्ड, widget अपडेट */
class PlaybackService : MediaSessionService() {
    companion object { const val ACTION_SLEEP = "com.example.musicplayer.SLEEP" }

    private var session: MediaSession? = null
    private val handler = Handler(Looper.getMainLooper())
    private val sleepRun = Runnable {
        session?.player?.pause()
        Store.setSleepEnd(this, 0L)
    }

    override fun onCreate() {
        super.onCreate()
        val player = ExoPlayer.Builder(this)
            .setAudioAttributes(AudioAttributes.DEFAULT, true)
            .setHandleAudioBecomingNoisy(true)
            .setWakeMode(C.WAKE_MODE_LOCAL)
            .build()
        player.addListener(object : Player.Listener {
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                mediaItem?.toTrack()?.let { Store.recordPlay(this@PlaybackService, it) }
            }
            override fun onEvents(p: Player, events: Player.Events) { push(p) }
        })
        session = MediaSession.Builder(this, player).build()
    }

    private fun push(p: Player) {
        val m = p.mediaMetadata
        WidgetUi.save(
            this, m.title?.toString() ?: "", m.artist?.toString() ?: "",
            p.isPlaying, p.repeatMode, p.shuffleModeEnabled
        )
        WidgetUi.updateAll(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_SLEEP) {
            handler.removeCallbacks(sleepRun)
            val min = intent.getIntExtra("min", 0)
            if (min > 0) {
                handler.postDelayed(sleepRun, min * 60_000L)
                Store.setSleepEnd(this, System.currentTimeMillis() + min * 60_000L)
            } else Store.setSleepEnd(this, 0L)
            return START_NOT_STICKY
        }
        return super.onStartCommand(intent, flags, startId)
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo) = session

    override fun onDestroy() {
        handler.removeCallbacks(sleepRun)
        session?.run { player.release(); release() }
        session = null
        super.onDestroy()
    }
}
''',
'app/src/main/java/com/example/musicplayer/Widget.kt': r'''package com.example.musicplayer

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.widget.RemoteViews
import androidx.core.content.ContextCompat
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken

object WidgetUi {
    private const val P = "com.example.musicplayer.W_"
    const val A_PREV = P + "PREV"; const val A_NEXT = P + "NEXT"; const val A_PLAY = P + "PLAY"
    const val A_STOP = P + "STOP"; const val A_REPEAT = P + "REPEAT"; const val A_SHUFFLE = P + "SHUFFLE"
    const val PREFIX = P
    private val ON = Color.parseColor("#FFEB3B")
    private val OFF = Color.parseColor("#88FFFFFF")

    private fun sp(c: Context) = c.getSharedPreferences("widget", Context.MODE_PRIVATE)

    fun save(c: Context, title: String, artist: String, playing: Boolean, repeat: Int, shuffle: Boolean) {
        sp(c).edit().putString("title", title).putString("artist", artist)
            .putBoolean("playing", playing).putInt("repeat", repeat).putBoolean("shuffle", shuffle).apply()
    }

    fun updateAll(ctx: Context) {
        val mgr = AppWidgetManager.getInstance(ctx)
        for ((cls, small) in listOf(Widget4x1Provider::class.java to true, Widget4x2Provider::class.java to false)) {
            val ids = mgr.getAppWidgetIds(ComponentName(ctx, cls))
            if (ids.isNotEmpty()) mgr.updateAppWidget(ids, build(ctx, small))
        }
    }

    private fun bind(v: RemoteViews, ctx: Context, small: Boolean, id: Int, action: String) {
        val cls = if (small) Widget4x1Provider::class.java else Widget4x2Provider::class.java
        val pi = PendingIntent.getBroadcast(
            ctx, action.hashCode() xor (if (small) 1 else 2), Intent(ctx, cls).setAction(action),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        v.setOnClickPendingIntent(id, pi)
    }

    fun build(ctx: Context, small: Boolean): RemoteViews {
        val s = sp(ctx)
        val title = s.getString("title", "") ?: ""
        val playing = s.getBoolean("playing", false)
        val repeat = s.getInt("repeat", 0)
        val shuffle = s.getBoolean("shuffle", false)
        val v = RemoteViews(ctx.packageName, if (small) R.layout.widget_4x1 else R.layout.widget_4x2)
        v.setTextViewText(R.id.w_title, title.ifEmpty { "Music Player" })
        v.setImageViewResource(R.id.w_play, if (playing) R.drawable.ic_pause else R.drawable.ic_play)
        bind(v, ctx, small, R.id.w_prev, A_PREV)
        bind(v, ctx, small, R.id.w_play, A_PLAY)
        bind(v, ctx, small, R.id.w_stop, A_STOP)
        bind(v, ctx, small, R.id.w_next, A_NEXT)
        val open = PendingIntent.getActivity(
            ctx, 0, Intent(ctx, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        v.setOnClickPendingIntent(R.id.w_title, open)
        if (!small) {
            v.setTextViewText(R.id.w_sub, s.getString("artist", "") ?: "")
            v.setOnClickPendingIntent(R.id.w_logo, open)
            bind(v, ctx, false, R.id.w_shuffle, A_SHUFFLE)
            bind(v, ctx, false, R.id.w_repeat, A_REPEAT)
            v.setImageViewResource(R.id.w_repeat, if (repeat == 1) R.drawable.ic_repeat_one else R.drawable.ic_repeat)
            v.setInt(R.id.w_repeat, "setColorFilter", if (repeat == 0) OFF else ON)
            v.setInt(R.id.w_shuffle, "setColorFilter", if (shuffle) ON else OFF)
        }
        return v
    }

    /** Widget बटन थिच्दा: player सँग जोडिएर आदेश पठाउने */
    fun run(ctx: Context, action: String, done: () -> Unit) {
        val app = ctx.applicationContext
        val token = SessionToken(app, ComponentName(app, PlaybackService::class.java))
        val f = MediaController.Builder(app, token).buildAsync()
        f.addListener({
            try { exec(f.get(), action) } catch (_: Exception) { }
            Handler(Looper.getMainLooper()).postDelayed({
                MediaController.releaseFuture(f); done()
            }, 600)
        }, ContextCompat.getMainExecutor(app))
    }

    private fun exec(c: MediaController, a: String) {
        when (a) {
            A_PREV -> c.seekToPreviousMediaItem()
            A_NEXT -> c.seekToNextMediaItem()
            A_PLAY -> if (c.isPlaying) c.pause() else {
                if (c.playbackState == Player.STATE_IDLE) c.prepare()
                if (c.playbackState == Player.STATE_ENDED) c.seekToDefaultPosition()
                c.play()
            }
            A_STOP -> { c.stop(); c.seekTo(0) }
            A_REPEAT -> c.repeatMode = nextRepeat(c.repeatMode)
            A_SHUFFLE -> c.shuffleModeEnabled = !c.shuffleModeEnabled
        }
    }
}

abstract class BaseWidget : AppWidgetProvider() {
    override fun onUpdate(context: Context, mgr: AppWidgetManager, ids: IntArray) = WidgetUi.updateAll(context)

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        val a = intent.action ?: return
        if (a.startsWith(WidgetUi.PREFIX)) {
            val pr = goAsync()
            WidgetUi.run(context, a) { pr.finish() }
        }
    }
}

class Widget4x1Provider : BaseWidget()
class Widget4x2Provider : BaseWidget()
''',
'app/src/main/java/com/example/musicplayer/YouTubeApi.kt': r'''package com.example.musicplayer

import androidx.core.text.HtmlCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class YtItem(val id: String, val title: String, val channel: String, val thumb: String)

/** YouTube Data API v3 बाट खोज्ने (केवल embed गर्न मिल्ने video) */
suspend fun searchYoutube(query: String): List<YtItem> = withContext(Dispatchers.IO) {
    require(BuildConfig.YT_API_KEY.isNotBlank()) { "YouTube API key राखिएको छैन (README हेर्नुहोस्)" }
    val q = URLEncoder.encode(query, "UTF-8")
    val url = URL(
        "https://www.googleapis.com/youtube/v3/search?part=snippet&type=video" +
            "&videoEmbeddable=true&maxResults=25&q=$q&key=${BuildConfig.YT_API_KEY}"
    )
    val conn = url.openConnection() as HttpURLConnection
    conn.connectTimeout = 10000
    conn.readTimeout = 10000
    try {
        if (conn.responseCode != 200) {
            val err = conn.errorStream?.bufferedReader()?.readText().orEmpty()
            error("API त्रुटि ${conn.responseCode}: ${err.take(200)}")
        }
        val items = JSONObject(conn.inputStream.bufferedReader().readText()).getJSONArray("items")
        List(items.length()) { i ->
            val o = items.getJSONObject(i)
            val s = o.getJSONObject("snippet")
            YtItem(
                id = o.getJSONObject("id").getString("videoId"),
                title = HtmlCompat.fromHtml(s.getString("title"), HtmlCompat.FROM_HTML_MODE_LEGACY).toString(),
                channel = s.getString("channelTitle"),
                thumb = s.getJSONObject("thumbnails").getJSONObject("medium").getString("url")
            )
        }
    } finally {
        conn.disconnect()
    }
}
''',
'app/src/main/java/com/example/musicplayer/Yt.kt': r'''package com.example.musicplayer

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.LifecycleOwner
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import coil.compose.AsyncImage
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.YouTubePlayer
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.listeners.AbstractYouTubePlayerListener
import com.pierfrancescosoffritti.androidyoutubeplayer.core.player.views.YouTubePlayerView
import kotlinx.coroutines.launch

@Composable
fun YouTubeTab(ytId: String?, onSelect: (String) -> Unit) {
    val scope = rememberCoroutineScope()
    var query by remember { mutableStateOf("") }
    var results by remember { mutableStateOf(emptyList<YtItem>()) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    fun search() {
        if (query.isBlank()) return
        scope.launch {
            loading = true; error = null
            try { results = searchYoutube(query.trim()) }
            catch (e: Exception) { error = "खोज्न सकिएन। इन्टरनेट/API key जाँच्नुहोस्।\n${e.message}" }
            loading = false
        }
    }

    Column(Modifier.fillMaxSize()) {
        if (ytId != null) YtPlayer(ytId, Modifier.fillMaxWidth().aspectRatio(16f / 9f))
        OutlinedTextField(
            value = query, onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            placeholder = { Text("YouTube मा खोज्नुहोस्") }, singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { search() }),
            trailingIcon = { TextButton({ search() }) { Text("खोज") } }
        )
        if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(12.dp)) }
        LazyColumn {
            items(results) { v ->
                Row(
                    Modifier.fillMaxWidth().clickable { onSelect(v.id) }.padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AsyncImage(v.thumb, null, Modifier.width(120.dp).aspectRatio(16f / 9f))
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text(v.title, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        Text(v.channel, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                    }
                }
            }
        }
    }
}

@Composable
fun YtPlayer(videoId: String, modifier: Modifier) {
    val lifecycle = (LocalContext.current as LifecycleOwner).lifecycle
    var yt by remember { mutableStateOf<YouTubePlayer?>(null) }
    var view by remember { mutableStateOf<YouTubePlayerView?>(null) }
    AndroidView(modifier = modifier, factory = { ctx ->
        YouTubePlayerView(ctx).apply {
            lifecycle.addObserver(this)
            addYouTubePlayerListener(object : AbstractYouTubePlayerListener() {
                override fun onReady(youTubePlayer: YouTubePlayer) { yt = youTubePlayer }
            })
            view = this
        }
    })
    LaunchedEffect(yt, videoId) { yt?.loadVideo(videoId, 0f) }
    DisposableEffect(Unit) { onDispose { view?.release() } }
}
''',
'app/src/main/res/drawable/ic_next.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M6,18l8.5,-6L6,6v12zM16,6v12h2V6h-2z"/>
</vector>
''',
'app/src/main/res/drawable/ic_pause.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M6,19h4V5H6v14zM14,5v14h4V5h-4z"/>
</vector>
''',
'app/src/main/res/drawable/ic_play.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M8,5v14l11,-7z"/>
</vector>
''',
'app/src/main/res/drawable/ic_prev.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M6,6h2v12H6zM9.5,12l8.5,6V6z"/>
</vector>
''',
'app/src/main/res/drawable/ic_repeat.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M7,7h10v3l4,-4 -4,-4v3H5v6h2V7zM17,17H7v-3l-4,4 4,4v-3h12v-6h-2v4z"/>
</vector>
''',
'app/src/main/res/drawable/ic_repeat_one.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M7,7h10v3l4,-4 -4,-4v3H5v6h2V7zM17,17H7v-3l-4,4 4,4v-3h12v-6h-2v4z"/>
    <path android:fillColor="#FFFFFFFF" android:pathData="M13,15V9h-1l-2,1v1h1.5v4H13z"/>
</vector>
''',
'app/src/main/res/drawable/ic_shuffle.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M10.59,9.17L5.41,4 4,5.41l5.17,5.17 1.42,-1.41zM14.5,4l2.04,2.04L4,18.59 5.41,20 17.96,7.46 20,9.5V4h-5.5zM14.83,13.41l-1.41,1.41 3.13,3.13L14.5,20H20v-5.5l-2.04,2.04 -3.13,-3.13z"/>
</vector>
''',
'app/src/main/res/drawable/ic_stop.xml': r'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M6,6h12v12H6z"/>
</vector>
''',
'app/src/main/res/drawable/widget_bg.xml': r'''<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="#EE0F1B4D"/>
    <corners android:radius="20dp"/>
    <stroke android:width="1dp" android:color="#55FFFFFF"/>
</shape>
''',
'app/src/main/res/layout/widget_4x1.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:orientation="horizontal" android:gravity="center_vertical"
    android:background="@drawable/widget_bg" android:padding="6dp">
    <TextView android:id="@+id/w_title" android:layout_width="0dp" android:layout_height="wrap_content"
        android:layout_weight="1.3" android:maxLines="2" android:ellipsize="end"
        android:paddingStart="8dp" android:paddingEnd="4dp"
        android:textColor="#FFFFFF" android:textSize="12sp" android:text="Music Player"/>
        <ImageButton android:id="@+id/w_prev" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="8dp" android:src="@drawable/ic_prev" android:contentDescription="w_prev"/>
        <ImageButton android:id="@+id/w_play" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="6dp" android:src="@drawable/ic_play" android:contentDescription="w_play"/>
        <ImageButton android:id="@+id/w_stop" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="9dp" android:src="@drawable/ic_stop" android:contentDescription="w_stop"/>
        <ImageButton android:id="@+id/w_next" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="8dp" android:src="@drawable/ic_next" android:contentDescription="w_next"/>
</LinearLayout>
''',
'app/src/main/res/layout/widget_4x2.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:orientation="vertical" android:background="@drawable/widget_bg" android:padding="10dp">
    <LinearLayout android:layout_width="match_parent" android:layout_height="wrap_content"
        android:orientation="horizontal" android:gravity="center_vertical">
        <ImageView android:id="@+id/w_logo" android:layout_width="44dp" android:layout_height="44dp"
            android:src="@mipmap/ic_launcher" android:contentDescription="logo"/>
        <LinearLayout android:layout_width="0dp" android:layout_height="wrap_content"
            android:layout_weight="1" android:orientation="vertical" android:paddingStart="10dp">
            <TextView android:id="@+id/w_title" android:layout_width="match_parent" android:layout_height="wrap_content"
                android:singleLine="true" android:ellipsize="end" android:textStyle="bold"
                android:textColor="#FFFFFF" android:textSize="14sp" android:text="Music Player"/>
            <TextView android:id="@+id/w_sub" android:layout_width="match_parent" android:layout_height="wrap_content"
                android:singleLine="true" android:ellipsize="end"
                android:textColor="#B0B8D0" android:textSize="12sp"/>
        </LinearLayout>
    </LinearLayout>
    <LinearLayout android:layout_width="match_parent" android:layout_height="0dp" android:layout_weight="1"
        android:orientation="horizontal" android:gravity="center">
        <ImageButton android:id="@+id/w_prev" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="10dp" android:src="@drawable/ic_prev" android:contentDescription="w_prev"/>
        <ImageButton android:id="@+id/w_play" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="8dp" android:src="@drawable/ic_play" android:contentDescription="w_play"/>
        <ImageButton android:id="@+id/w_stop" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="12dp" android:src="@drawable/ic_stop" android:contentDescription="w_stop"/>
        <ImageButton android:id="@+id/w_next" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="10dp" android:src="@drawable/ic_next" android:contentDescription="w_next"/>
    </LinearLayout>
    <LinearLayout android:layout_width="match_parent" android:layout_height="36dp"
        android:orientation="horizontal" android:gravity="center">
        <ImageButton android:id="@+id/w_shuffle" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="7dp" android:src="@drawable/ic_shuffle" android:contentDescription="w_shuffle"/>
        <ImageButton android:id="@+id/w_repeat" android:layout_width="0dp" android:layout_height="match_parent" android:layout_weight="1" android:background="@android:color/transparent" android:scaleType="centerInside" android:padding="7dp" android:src="@drawable/ic_repeat" android:contentDescription="w_repeat"/>
    </LinearLayout>
</LinearLayout>
''',
'app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
''',
'app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
''',
'app/src/main/res/values/colors.xml': r'''<resources><color name="ic_launcher_background">#0A1B5C</color></resources>
''',
'app/src/main/res/values/styles.xml': r'''<resources>
    <style name="AppTheme" parent="@android:style/Theme.DeviceDefault.NoActionBar" />
</resources>
''',
'app/src/main/res/xml/widget_4x1_info.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp" android:minHeight="40dp"
    android:targetCellWidth="4" android:targetCellHeight="1"
    android:updatePeriodMillis="0" android:initialLayout="@layout/widget_4x1"
    android:resizeMode="horizontal" android:widgetCategory="home_screen"/>
''',
'app/src/main/res/xml/widget_4x2_info.xml': r'''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp" android:minHeight="110dp"
    android:targetCellWidth="4" android:targetCellHeight="2"
    android:updatePeriodMillis="0" android:initialLayout="@layout/widget_4x2"
    android:resizeMode="horizontal|vertical" android:widgetCategory="home_screen"/>
''',
'build.gradle.kts': r'''plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
''',
'gradle.properties': r'''org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
''',
'gradle/wrapper/gradle-wrapper.properties': r'''distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.7-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
''',
'settings.gradle.kts': r'''pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "MusicPlayer"
include(":app")
''',
}
for path, text in FILES.items():
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

# ---- App icon: logo.png बाट सबै साइजका आइकन बनाउने ----
from PIL import Image, ImageDraw
if os.path.exists("logo.png"):
    src = Image.open("logo.png").convert("RGBA")
else:
    src = Image.new("RGBA", (512, 512), (15, 27, 77, 255))
w, h = src.size
m = Image.new("L", (w, h), 0)
ImageDraw.Draw(m).ellipse((w*0.012, h*0.012, w*0.988, h*0.988), fill=255)
src.putalpha(m)
logo = src.crop((int(w*0.012), int(h*0.012), int(w*0.988), int(h*0.988)))
for d, s in {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}.items():
    p = "app/src/main/res/mipmap-" + d
    os.makedirs(p, exist_ok=True)
    n = int(48*s)
    ic = logo.resize((n, n), Image.LANCZOS)
    ic.save(p + "/ic_launcher.png"); ic.save(p + "/ic_launcher_round.png")
    N = int(108*s); fg = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    L = int(N*0.62); l = logo.resize((L, L), Image.LANCZOS)
    fg.paste(l, ((N-L)//2, (N-L)//2), l)
    fg.save(p + "/ic_launcher_foreground.png")
print("project generated:", len(FILES), "files")
