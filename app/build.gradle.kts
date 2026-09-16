plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "jp.example.greenreader"
    compileSdk = 35

    defaultConfig {
        applicationId = "jp.example.greenreader"
        minSdk = 26
        targetSdk = 35
        versionCode = 27
        versionName = "0.8.7"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.documentfile:documentfile:1.0.1")
    implementation("com.google.android.material:material:1.12.0")
    implementation("com.google.ar:core:1.54.0")
    testImplementation("junit:junit:4.13.2")
}
