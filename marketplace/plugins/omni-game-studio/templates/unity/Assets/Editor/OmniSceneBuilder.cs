#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// 菜单工具：一键生成最小可运行场景。
/// 用法：菜单栏 Tools ▸ Omni ▸ Create Main Scene
/// 不自动执行——避免在你有未保存改动时擅自新建场景。
/// </summary>
public static class OmniSceneBuilder
{
    const string SceneDir = "Assets/Scenes";
    const string ScenePath = SceneDir + "/Main.unity";

    [MenuItem("Tools/Omni/Create Main Scene")]
    public static void CreateMainScene()
    {
        if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            return;

        Directory.CreateDirectory(SceneDir);
        var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

        var root = new GameObject("GameRoot");
        root.AddComponent<GameRoot>();

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        AssetDatabase.Refresh();
        Debug.Log($"[Omni] 已生成 {ScenePath} 并加入 Build Settings");
    }
}
#endif
