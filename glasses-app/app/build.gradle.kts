plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.bb.lucia"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.bb.lucia"
        minSdk = 26
        targetSdk = 28        // M6 = Android 9 (API 28), 640x480 @ 160 dpi
        versionCode = 1
        versionName = "0.1"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
