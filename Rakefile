# frozen_string_literal: true

require 'rake/clean'

require 'fileutils'

require 'zip'

NAME = 'ROGZIS'
VERSION = 3.3

CLEAN.include('./dist/*')
CLEAN.exclude('./dist/*.pk3')

desc 'Do everything!'
task default: [] do
  sh 'rake upgrade'
  sh 'rake compile'
  sh 'rake build'
  sh 'rake clean'
end

desc 'Updates submodules'
task :upgrade do
  sh 'git submodule foreach git pull origin master'
end

desc 'Compiles submods'
task :compile do
  first = true
  Dir.foreach('./packages/') do |package|
    next if (package == '.') || (package == '..')

    puts "Building: #{package.capitalize}"
    dest = "./packages/#{package.capitalize}"

    if first
      settings = "-V#{VERSION} "
      first = false
    else
      settings = ''
    end
    if File.exist?("#{dest}/SETTINGS")
      open("#{dest}/SETTINGS").each do |line|
        settings += line
      end
    end

    sh "python3 scripts/compile/bobby/build.py #{dest} #{settings}"
    puts '  Successful'
  end
end

desc 'Builds PK3 out of compiled submods'
task :build do
  FileUtils.rm_rf('./dist')
  Dir.mkdir './dist'
  Dir.chdir './packages'
  Dir.foreach('./') do |package|
    next if (package == '.') || (package == '..')

    puts Dir.pwd
    subdir = "./#{package}/dist/#{package.capitalize}/"
    Dir.foreach(subdir) do |item|
      next if (item == '.') || (item == '..')

      nItem = subdir + item
      if File.directory?(nItem)
        FileUtils.copy_entry(nItem, "../dist/#{item}")
      elsif File.file?(nItem)
        dest = "../dist/#{item}"
        if File.exist?(dest)
          open(dest, 'a') do |o|
            open(nItem, 'r').each do |line|
              o.puts(line)
            end
          end
        elsif
          FileUtils.copy(nItem, dest)
        end
      end
    end
  end

  Dir.chdir('../dist/')
  Zip::File.open("./#{NAME}.pk3", Zip::File::CREATE) do |zipFile|
    Dir.foreach('./') do |filename|
      zipFile.add(filename, filename)
    end
  end
end
