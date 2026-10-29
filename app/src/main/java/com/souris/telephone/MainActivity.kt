package com.souris.telephone

import android.annotation.SuppressLint
import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.WindowManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {

    private var web: WebView? = null
    private val handler = Handler(Looper.getMainLooper())
    private var timeout: Runnable? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        showForm()
    }

    private fun cancelTimeout() {
        timeout?.let { handler.removeCallbacks(it) }
        timeout = null
    }

    private fun fail(message: String) {
        cancelTimeout()
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        showForm()
    }

    private fun showForm() {
        cancelTimeout()
        web?.destroy()
        web = null
        val prefs = getSharedPreferences("souris", MODE_PRIVATE)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 120, 48, 48)
        }
        val title = TextView(this).apply {
            text = "Cedric souris pc"
            textSize = 24f
        }
        val ip = EditText(this).apply {
            hint = "Adresse du PC (ex : 192.168.1.20)"
            setText(prefs.getString("ip", ""))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
        }
        val pin = EditText(this).apply {
            hint = "Code PIN affiché sur le PC"
            setText(prefs.getString("pin", ""))
            inputType = InputType.TYPE_CLASS_NUMBER
        }
        val btn = Button(this).apply {
            text = "Connecter"
            setOnClickListener {
                val a = ip.text.toString().trim()
                val p = pin.text.toString().trim()
                if (a.isEmpty() || p.isEmpty()) {
                    Toast.makeText(context, "Remplis l'adresse et le PIN", Toast.LENGTH_SHORT).show()
                } else {
                    prefs.edit().putString("ip", a).putString("pin", p).apply()
                    connect(a, p)
                }
            }
        }
        layout.addView(title)
        layout.addView(ip)
        layout.addView(pin)
        layout.addView(btn)
        setContentView(layout)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun connect(address: String, pin: String) {
        val host = if (address.contains(":")) address else "$address:8765"
        val view = WebView(this)
        view.setBackgroundColor(Color.parseColor("#0F1115"))
        view.settings.javaScriptEnabled = true
        view.settings.domStorageEnabled = true
        view.webViewClient = object : WebViewClient() {
            override fun onPageFinished(v: WebView, url: String) {
                cancelTimeout()
            }

            override fun onReceivedError(
                v: WebView, request: WebResourceRequest, error: WebResourceError
            ) {
                if (request.isForMainFrame) {
                    fail("Connexion impossible. Vérifie l'IP, le WiFi, et que le programme tourne sur le PC.")
                }
            }

            override fun onReceivedHttpError(
                v: WebView, request: WebResourceRequest, errorResponse: WebResourceResponse
            ) {
                if (request.isForMainFrame) {
                    if (errorResponse.statusCode == 403) fail("PIN incorrect.")
                    else fail("Erreur du serveur (${errorResponse.statusCode}).")
                }
            }
        }
        web = view
        setContentView(view)
        timeout = Runnable {
            fail("Pas de réponse du PC après 10 secondes. Pare-feu Windows, mauvaise IP ou WiFi différent ?")
        }
        handler.postDelayed(timeout!!, 10000)
        view.loadUrl("http://$host/?k=$pin")
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web != null) showForm() else super.onBackPressed()
    }
}
