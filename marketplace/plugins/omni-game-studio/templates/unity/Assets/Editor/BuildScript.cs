#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

/// <summary>
/// 批处理构建入口，供 build_check.py / CI 调用：
///   Unity.exe -quit -batchmode -nographics -projectPath "<项目>" \
///             -executeMethod BuildScript.PerformBuild -logFile -
/// 修改 BuildTarget 与 OutputDir 以匹配你的目标平台。
/// </summary>
public static class BuildScript
{
    const string OutputDir = "build/StandaloneWindows64";
    const BuildTarget Target = BuildTarget.StandaloneWindows64;
    const string ScenePath = "Assets/Scenes/Main.unity";

    [MenuItem("Tools/Omni/Build (batch entry)")]
    public static void PerformBuild()
    {
        Directory.CreateDirectory(OutputDir);

        var options = new BuildPlayerOptions
        {
            scenes = File.Exists(ScenePath) ? new[] { ScenePath } : new string[0],
            locationPathName = Path.Combine(OutputDir, "game.exe"),
            target = Target,
            options = BuildOptions.None,
        };

        BuildReport report = BuildPipeline.BuildPlayer(options);
        var summary = report.summary;

        if (summary.result == BuildResult.Succeeded)
        {
            Debug.Log($"[Omni] 构建成功: {summary.outputPath}  {summary.totalSize / 1024 / 1024} MB");
            EditorApplication.Exit(0);
        }
        else
        {
            Debug.LogError($"[Omni] 构建失败: {summary.result}  错误 {summary.totalErrors}");
            EditorApplication.Exit(1);
        }
    }
}
#endif
