package jp.example.greenreader

import android.Manifest
import android.content.pm.PackageManager
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.view.Gravity
import android.view.MotionEvent
import android.view.Surface
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.ar.core.*
import com.google.ar.core.exceptions.CameraNotAvailableException
import com.google.ar.core.exceptions.UnavailableException
import jp.example.greenreader.analysis.*
import jp.example.greenreader.ar.BackgroundRenderer
import jp.example.greenreader.ui.ProfileView
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class MainActivity : AppCompatActivity(), GLSurfaceView.Renderer {
    private lateinit var gl:GLSurfaceView
    private lateinit var status:TextView
    private lateinit var profile:ProfileView
    private lateinit var stimp:SeekBar
    private lateinit var stimpLabel:TextView
    private var session:Session?=null
    private val bg=BackgroundRenderer()
    private val collector=DepthCollector()
    @Volatile private var latestFrame:Frame?=null
    private var scanning=false
    private var markMode=0 // 1 ball, 2 cup
    private var ball:Vec3?=null
    private var cup:Vec3?=null
    private var grain:GrainReport?=null
    private var viewportW=1; private var viewportH=1

    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState)
        buildUi()
        if(ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){
            ActivityCompat.requestPermissions(this,arrayOf(Manifest.permission.CAMERA),100)
        }
    }

    private fun buildUi(){
        val root=FrameLayout(this)
        gl=GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setRenderer(this@MainActivity)
            renderMode=GLSurfaceView.RENDERMODE_CONTINUOUSLY
            setOnTouchListener { _, ev ->
                if (ev.action == MotionEvent.ACTION_UP && markMode != 0) {
                    markAt(ev.x, ev.y)
                    true
                } else {
                    markMode != 0
                }
            }
        }
        root.addView(gl,FrameLayout.LayoutParams(-1,-1))

        val panel=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL; setPadding(18,18,18,18)
            setBackgroundColor(0xAA111111.toInt())
        }
        status=TextView(this).apply { text="①ボール ②カップ ③スキャン開始"; setTextColor(0xffffffff.toInt()); textSize=16f }
        panel.addView(status)

        val row=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
        fun button(text:String, action:()->Unit)=Button(this).apply { this.text=text; setOnClickListener{action()} }
        row.addView(button("ボール"){ markMode=1; status.text="画面上のボール位置をタップ" },LinearLayout.LayoutParams(0,-2,1f))
        row.addView(button("カップ"){ markMode=2; status.text="画面上のカップ位置をタップ" },LinearLayout.LayoutParams(0,-2,1f))
        row.addView(button("スキャン"){ scanning=!scanning; if(scanning){collector.clear(); status.text="ゆっくり左右に動かしてスキャン中…"}else analyze() },LinearLayout.LayoutParams(0,-2,1f))
        panel.addView(row)

        val row2=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
        row2.addView(button("芝目軸解析"){ analyzeGrain() },LinearLayout.LayoutParams(0,-2,1f))
        row2.addView(button("解析"){ analyze() },LinearLayout.LayoutParams(0,-2,1f))
        row2.addView(button("リセット"){ ball=null; cup=null; grain=null; collector.clear(); profile.report=null; status.text="リセットしました" },LinearLayout.LayoutParams(0,-2,1f))
        panel.addView(row2)

        stimpLabel=TextView(this).apply { setTextColor(0xffffffff.toInt()); text="Stimp: 9.0" }
        panel.addView(stimpLabel)
        stimp=SeekBar(this).apply {
            max=50; progress=20
            setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener{
                override fun onProgressChanged(s:SeekBar?,p:Int,from:Boolean){ stimpLabel.text=String.format("Stimp: %.1f",7f+p/10f) }
                override fun onStartTrackingTouch(s:SeekBar?){}
                override fun onStopTrackingTouch(s:SeekBar?){}
            })
        }
        panel.addView(stimp)

        profile=ProfileView(this).apply { setBackgroundColor(0xCCFFFFFF.toInt()) }
        panel.addView(profile,LinearLayout.LayoutParams(-1,280))

        val lp=FrameLayout.LayoutParams(-1,-2).apply { gravity=Gravity.BOTTOM }
        root.addView(panel,lp)
        setContentView(root)
    }

    override fun onResume(){
        super.onResume()
        if(ContextCompat.checkSelfPermission(this,Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)return
        try {
            if(session==null){
                when(ArCoreApk.getInstance().requestInstall(this,true)){
                    ArCoreApk.InstallStatus.INSTALL_REQUESTED -> return
                    else -> {}
                }
                session=Session(this).also { s ->
                    val c=Config(s).apply {
                        focusMode=Config.FocusMode.AUTO
                        planeFindingMode=Config.PlaneFindingMode.HORIZONTAL
                        if(s.isDepthModeSupported(Config.DepthMode.AUTOMATIC)) depthMode=Config.DepthMode.AUTOMATIC
                    }
                    s.configure(c)
                }
            }
            session?.resume(); gl.onResume()
        } catch(e:UnavailableException){ status.text="ARCoreを開始できません: ${e.message}" }
        catch(e:CameraNotAvailableException){ status.text="カメラを開始できません" }
    }

    override fun onPause(){ super.onPause(); gl.onPause(); session?.pause() }

    override fun onSurfaceCreated(unused:GL10?,config:EGLConfig?){ GLES20.glClearColor(0f,0f,0f,1f); bg.createOnGlThread(); session?.setCameraTextureName(bg.textureId) }
    override fun onSurfaceChanged(unused:GL10?,w:Int,h:Int){ viewportW=w; viewportH=h; GLES20.glViewport(0,0,w,h) }

    override fun onDrawFrame(unused:GL10?){
        val s=session ?: return
        try {
            s.setDisplayGeometry(display?.rotation ?: Surface.ROTATION_0,viewportW,viewportH)
            if(bg.textureId!=-1) s.setCameraTextureName(bg.textureId)
            val f=s.update(); latestFrame=f
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
            bg.draw(f)
            if(scanning && f.camera.trackingState==TrackingState.TRACKING) collector.integrate(f)
        } catch(_:Throwable){}
    }

    private fun markAt(x:Float,y:Float){
        val f=latestFrame ?: run {
            status.text="ARの準備中です。端末を少し動かしてから再試行してください"
            return
        }
        val hit=f.hitTest(x,y).firstOrNull { h ->
            val t=h.trackable
            (t is Plane && t.isPoseInPolygon(h.hitPose)) || t is DepthPoint || t is Point
        } ?: run { status.text="位置を取得できません。端末を少し動かして再試行してください"; return }
        val p=hit.hitPose.translation.let{Vec3(it[0],it[1],it[2])}
        if(markMode==1){ball=p;status.text="ボール位置を設定しました。次にカップを設定"}else{cup=p;status.text="カップ位置を設定しました。スキャン開始してください"}
        markMode=0
    }

    private fun analyzeGrain(){
        val f=latestFrame ?: return
        grain=GrainEstimator.estimate(f)
        val g=grain
        status.text= if(g==null) "芝画像を取得できません。少し動かして再試行" else String.format("芝目軸 %.0f° / 信頼度 %.0f%% ※方向(順/逆)は未確定",g.axisDegrees,g.confidence*100)
    }

    private fun analyze(){
        scanning=false
        val b=ball; val c=cup
        if(b==null||c==null){ status.text="先にボールとカップを設定してください"; return }
        val report=SlopeAnalyzer.analyze(collector.snapshot(),b,c)
        if(report==null){ status.text="解析に必要な点が不足しています。パットラインをゆっくりスキャンしてください"; return }
        profile.report=report
        val st=7f+stimp.progress/10f
        val adv=PuttAdvisor.advise(report,st,grain)
        val dir=if(adv.aimOffsetCm>=0)"左" else "右"
        status.text=String.format(
            "距離 %.2fm / 縦 %.1f%% / 横 %.1f%% / %s %.0fcm狙い(実験) / 実質 %.2fm / 点%d",
            report.distanceMeters,report.overallLongitudinalPercent,report.overallCrossPercent,dir,kotlin.math.abs(adv.aimOffsetCm),adv.effectiveDistanceM,report.pointCount
        )
    }

    override fun onRequestPermissionsResult(req:Int,perms:Array<out String>,res:IntArray){
        super.onRequestPermissionsResult(req,perms,res)
        if(req==100 && res.firstOrNull()==PackageManager.PERMISSION_GRANTED) recreate()
    }
}
