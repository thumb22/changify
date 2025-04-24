module.exports = {
    apps: [
        {
            name: "changify-bot",
            script: "main.py",
            interpreter: "./venv/bin/python3",
            env: {
                NODE_ENV: "production",
            },
            watch: false,
            max_memory_restart: "200M",
            log_date_format: "YYYY-MM-DD HH:mm Z",
            error_file: "logs/pm2_error.log",
            out_file: "logs/pm2_out.log",
            time: true,
        },
    ],
};
