plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val greenReaderKeystorePath = System.getenv("GREEN_READER_KEYSTORE_PATH")
val greenReaderStorePassword = System.getenv("GREEN_READER_STORE_PASSWORD")
val greenReaderKeyAlias = System.getenv("GREEN_READER_KEY_ALIAS")
val greenReaderKeyPassword = System.getenv("GREEN_READER_KEY_PASSWORD")
val hasGreenReaderSigning =
    !greenReaderKeystorePath.isNullOrBlank() &&
    !greenReaderStorePassword.isNullOrBlank() &&
    !greenReaderKeyAlias.isNullOrBlank() &&
    !greenReaderKeyPassword.isNullOrBlank()

android {
    namespace = "jp.example.greenreader"
    compileSdk = 35

    defaultConfig {
        applicationId = "jp.example.greenreader"
        minSdk = 26
        targetSdk = 35
        versionCode = 39
        versionName = "0.8.19"
    }

    signingConfigs {
        if (hasGreenReaderSigning) {
            create("greenReaderRelease") {
                storeFile = file(greenReaderKeystorePath!!)
                storePassword = greenReaderStorePassword
                keyAlias = greenReaderKeyAlias
                keyPassword = greenReaderKeyPassword
            }
        }
    }

    buildTypes {
        getByName("release") {
            if (hasGreenReaderSigning) {
                signingConfig = signingConfigs.getByName("greenReaderRelease")
            }
            isMinifyEnabled = false
        }
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
    implementation("com.google.android.gms:play-services-auth:21.6.0")
    testImplementation("junit:junit:4.13.2")
}
