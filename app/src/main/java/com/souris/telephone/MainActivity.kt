package com.souris.telephone

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.view.WindowManager
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {

    private var web: WebView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        showForm()
    }

    private fun showForm() {
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
        view.settings.javaScriptEnabled = true
        view.settings.domStorageEnabled = true
        view.webViewClient = object : WebViewClient() {
            override fun onReceivedError(
                v: WebView, request: WebResourceRequest, error: WebResourceError
            ) {
                if (request.isForMainFrame) {
                    Toast.makeText(
                        this@MainActivity,
                        "Connexion impossible. Le serveur tourne sur le PC ?",
                        Toast.LENGTH_LONG
                    ).show()
                    showForm()
                }
            }
        }
        web = view
        setContentView(view)
        view.loadUrl("http://$host/?k=$pin")
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web != null) showForm() else super.onBackPressed()
    }
}
