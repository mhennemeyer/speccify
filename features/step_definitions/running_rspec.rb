Given /^the following spec:$/ do |spec|
  @path = "/tmp/example_spec.rb"
  File.open(@path, "w") do |f|
    f.write spec
  end
end

When /^I run it with the (.*)$/ do |interpreter|
  stderr_file = Tempfile.new('rspec')
  stderr_file.close
  @stdout = case(interpreter)
    when /^ruby interpreter/
      args = interpreter.gsub('ruby interpreter','')
      ruby("#{@path}#{args}", stderr_file.path)
    when /^ruby1.9 interpreter/
      args = interpreter.gsub('ruby1.9 interpreter','')
      ruby19("#{@path}#{args}", stderr_file.path)
    else raise "Unknown interpreter: #{interpreter}"
  end
  @stderr = IO.read(stderr_file.path)
  @exit_code = $?.to_i
end

Then /^the (.*) should match (.*)$/ do |stream, string|
  written = case(stream)
    when 'stdout' then @stdout
    when 'stderr' then @stderr
    else raise "Unknown stream: #{stream}"
  end
  written.should match(string)
end

Then /^the (.*) should be blank$/ do |stream|
  written = case(stream)
    when 'stdout' then @stdout
    when 'stderr' then @stderr
    else raise "Unknown stream: #{stream}"
  end
  written.should be_blank
end

Then /^the (.*) should not match (.*)$/ do |stream, string|
  written = case(stream)
    when 'stdout' then @stdout
    when 'stderr' then @stderr
    else raise "Unknown stream: #{stream}"
  end
  written.should_not match(string)
end
# 
# Then /^the exit code should be (\d+)$/ do |exit_code|
#   if @exit_code != exit_code.to_i
#     raise "Did not exit with #{exit_code}, but with #{@exit_code}. Standard error:\n#{@stderr}"
#   end
# end
